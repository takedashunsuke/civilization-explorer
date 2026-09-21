"""LLM decision layer (Ollama / OpenAI). Failures fall back to heuristics in engine."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from config import get_settings
from simulation.models import (
    ActionType,
    AgentState,
    ChosenAction,
    RegionPolicy,
    RegionReading,
    SimulationState,
)

logger = logging.getLogger(__name__)

_ALLOWED_ACTIONS = {
    ActionType.wait,
    ActionType.cooperate,
    ActionType.conflict,
    ActionType.migrate,
    ActionType.obey,
    ActionType.resist,
}
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_ALLOWED_GROUP_ACTIONS = {
    ActionType.wait,
    ActionType.cooperate,
    ActionType.conflict,
    ActionType.migrate,
    ActionType.obey,
    ActionType.resist,
}
_ARCHETYPES = {"reformer", "warlord", "merchant", "priest", "bureaucrat", "explorer", "none"}
_TRAJECTORIES = {"war", "industry", "reform", "stagnation", "exodus", "faith"}
_ARCHETYPE_JA = {
    "reformer": "改革者",
    "warlord": "軍事指導者",
    "merchant": "商人",
    "priest": "宗教家",
    "bureaucrat": "官僚",
    "explorer": "探検家",
    "none": "特になし",
}
_TRAJECTORY_JA = {
    "war": "戦争",
    "industry": "産業",
    "reform": "改革",
    "stagnation": "停滞",
    "exodus": "流出",
    "faith": "信仰",
}


def _narrative_lang() -> str:
    lang = (get_settings().llm_narrative_lang or "ja").strip().lower()
    return lang if lang in {"ja", "en"} else "ja"


def _narrative_instruction() -> str:
    if _narrative_lang() == "en":
        return "summary and reason must be short natural English. "
    return (
        "summary and reason MUST be short natural Japanese (日本語). "
        "Do not write English prose in those fields. "
    )


def describe_provider() -> dict[str, Any]:
    settings = get_settings()
    provider = (settings.llm_provider or "stub").strip().lower()
    wired = provider in {"ollama", "openai"}
    return {
        "provider": provider,
        "ollama_model": settings.ollama_model,
        "openai_model": settings.openai_model,
        "wired": wired,
        "mode": "group+sample",
        "max_agents_per_turn": settings.llm_max_agents_per_turn,
        "group_sample_per_region": settings.llm_group_sample_per_region,
        "timeout_sec": settings.llm_timeout_sec,
        "note": (
            f"Group stance (≤{settings.llm_group_sample_per_region} actors/region) plus "
            f"≤{settings.llm_max_agents_per_turn} sample-resident LLM overrides per region."
            if wired
            else "Group stance uses heuristic stub; sample-resident overrides are off."
        ),
    }


def build_observation(
    sim: SimulationState,
    agent: AgentState,
    neighbors: list[tuple[AgentState, float, float]],
) -> dict[str, Any]:
    region = next((r for r in sim.world.regions if r.id.value == agent.region_id), None)
    institution = (region.institution if region else sim.world.institution).value
    tax = region.tax_rate if region else sim.world.tax_rate
    authority = (
        region.institution_runtime.authority
        if region
        else sim.world.institution_runtime.authority
    )
    policy = next((p for p in sim.region_policies if p.region_id == agent.region_id), None)
    reading = next((r for r in sim.region_readings if r.region_id == agent.region_id), None)
    return {
        "self": {
            "id": agent.id,
            "name": agent.name,
            "wealth": round(agent.wealth, 2),
            "energy": round(agent.energy, 2),
            "happiness": round(agent.happiness, 2),
            "personality": {
                "cooperation": round(agent.personality.cooperation, 2),
                "aggression": round(agent.personality.aggression, 2),
                "ambition": round(agent.personality.ambition, 2),
            },
            "traits": list(agent.traits),
            "goal": agent.goal,
            "allegiance": agent.allegiance.value,
            "memory": agent.memory[-3:],
        },
        "world": {
            "turn": sim.world.turn,
            "institution": institution,
            "tax_rate": round(tax, 2),
            "authority": round(authority, 2),
            "resource_pool": round((region.resource_pool if region else sim.world.resource_pool), 1),
            "region": agent.region_id,
            "subregion": agent.subregion_id,
            "climate": (region.climate.value if region else sim.world.climate.value),
            "region_mood": reading.summary if reading else "",
            "region_trajectory": reading.trajectory if reading else "",
            "rising_archetype": reading.rising_archetype if reading else "",
            "discontent": round(reading.discontent, 2) if reading else None,
            "group_action": policy.action.value if policy else "wait",
            "group_intensity": round(policy.intensity, 2) if policy else None,
        },
        "neighbors": [
            {
                "id": other.id,
                "trust": round(trust, 2),
                "distance": round(dist, 1),
                "traits": list(other.traits)[:2],
            }
            for other, trust, dist in neighbors[:5]
        ],
        "actions": ["wait", "cooperate", "conflict", "migrate", "obey", "resist"],
    }


def build_prompt(observation: dict[str, Any]) -> str:
    self_info = observation["self"]
    world = observation["world"]
    neighbors = observation["neighbors"]
    neighbor_ids = ", ".join(n["id"] for n in neighbors) or "(none)"
    neighbor_lines = ", ".join(
        f"{n['id']} trust={n['trust']}" for n in neighbors
    ) or "none"
    traits = ",".join(self_info.get("traits") or []) or "none"
    mood = world.get("region_mood") or "unknown"
    traj = world.get("region_trajectory") or "unknown"
    if _narrative_lang() == "en":
        reason_hint = (
            'Example: {"action":"obey","target_id":null,"reason":"authority still holds"}\n'
            "reason = short English cause.\n"
        )
    else:
        reason_hint = (
            'Example: {"action":"obey","target_id":null,"reason":"権威がまだ保たれている"}\n'
            "reason = 短い日本語の理由。\n"
        )
    return (
        "Society simulation. Pick ONE action. Reply JSON only.\n"
        f"{reason_hint}"
        "Actions: wait, cooperate, conflict, migrate, obey, resist.\n"
        f"cooperate/conflict target_id must be one of: {neighbor_ids}. "
        "Other actions use target_id null.\n"
        f"You id={self_info['id']} wealth={self_info['wealth']} "
        f"energy={self_info['energy']} happiness={self_info['happiness']} "
        f"coop={self_info['personality']['cooperation']} "
        f"agg={self_info['personality']['aggression']} "
        f"amb={self_info['personality']['ambition']} "
        f"traits={traits} goal={self_info['goal']} "
        f"allegiance={self_info['allegiance']}.\n"
        f"World turn={world['turn']} institution={world['institution']} "
        f"tax={world['tax_rate']} authority={world['authority']} "
        f"region={world['region']} climate={world.get('climate')}.\n"
        f"Region trajectory={traj}; mood={mood}; "
        f"rising={world.get('rising_archetype') or 'none'}; "
        f"discontent={world.get('discontent')}; "
        f"group_stance={world.get('group_action') or 'wait'}. "
        "You may follow the group stance or deviate.\n"
        f"Neighbors: {neighbor_lines}."
    )


def parse_decision(text: str, neighbor_ids: list[str] | set[str]) -> ChosenAction | None:
    if not text:
        return None
    raw = text.strip()
    payload: dict[str, Any] | None = None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_RE.search(raw)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = None
    if not isinstance(payload, dict):
        return None

    action_raw = str(payload.get("action", "")).strip().lower()
    try:
        action = ActionType(action_raw)
    except ValueError:
        return None
    if action not in _ALLOWED_ACTIONS:
        return None

    ordered_neighbors = list(neighbor_ids)
    neighbor_set = set(ordered_neighbors)

    target_id = payload.get("target_id")
    if target_id in ("", "null", "none", "None"):
        target_id = None
    if isinstance(target_id, str):
        target_id = target_id.strip() or None
    else:
        target_id = None

    if action in {ActionType.cooperate, ActionType.conflict}:
        if not target_id or target_id not in neighbor_set:
            # Tiny models invent ids; fall back to nearest listed neighbor.
            if ordered_neighbors:
                target_id = ordered_neighbors[0]
            else:
                return None
    else:
        # Tiny models often invent a target for wait/migrate; ignore it.
        target_id = None

    rationale = str(payload.get("reason") or payload.get("rationale") or "").strip()
    rationale = re.sub(r"^(short\s+why|reason)\s*:\s*", "", rationale, flags=re.I).strip()
    if len(rationale) > 180:
        rationale = rationale[:177] + "..."

    return ChosenAction(
        agent_id="",  # filled by caller
        action=action,
        target_id=target_id,
        reason="",
        source="llm",
        rationale=rationale or f"llm:{action.value}",
    )


def _post_json(url: str, body: dict[str, Any], timeout: float, headers: dict[str, str] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_ollama(prompt: str, *, num_predict: int = 96) -> str:
    settings = get_settings()
    base = settings.ollama_base_url.rstrip("/")
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.35,
            "num_predict": num_predict,
        },
    }
    # Region observe needs a longer budget than single-agent decisions.
    timeout = max(settings.llm_timeout_sec, 12.0 if num_predict > 160 else settings.llm_timeout_sec)
    result = _post_json(f"{base}/api/chat", payload, timeout=timeout)
    message = result.get("message") or {}
    return str(message.get("content") or "")


def _call_openai(prompt: str, *, num_predict: int = 96) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is empty")
    payload = {
        "model": settings.openai_model,
        "temperature": 0.35,
        "max_tokens": max(120, num_predict),
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Return only a JSON object.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    timeout = max(settings.llm_timeout_sec, 12.0 if num_predict > 160 else settings.llm_timeout_sec)
    result = _post_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        timeout=timeout,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
    )
    choices = result.get("choices") or []
    if not choices:
        return ""
    return str((choices[0].get("message") or {}).get("content") or "")


def complete_decision_text(prompt: str, *, num_predict: int = 96) -> str:
    settings = get_settings()
    provider = (settings.llm_provider or "stub").strip().lower()
    if provider == "ollama":
        return _call_ollama(prompt, num_predict=num_predict)
    if provider == "openai":
        return _call_openai(prompt, num_predict=num_predict)
    raise RuntimeError(f"LLM provider '{provider}' is not wired")


def decide_one(
    sim: SimulationState,
    agent: AgentState,
    neighbors: list[tuple[AgentState, float, float]],
) -> ChosenAction | None:
    neighbor_ids = [n.id for n, _, _ in neighbors]
    observation = build_observation(sim, agent, neighbors)
    prompt = build_prompt(observation)
    try:
        text = complete_decision_text(prompt)
        choice = parse_decision(text, neighbor_ids)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, OSError) as exc:
        logger.info("LLM decide failed for %s: %s", agent.id, exc)
        return None
    except Exception as exc:  # noqa: BLE001 — never break the sim tick
        logger.warning("LLM unexpected error for %s: %s", agent.id, exc)
        return None
    if choice is None:
        return None
    choice.agent_id = agent.id
    return choice


def select_llm_agents(sim: SimulationState, rng: Any) -> list[AgentState]:
    """Pick a small set of socially salient agents for LLM decisions each turn."""
    settings = get_settings()
    limit = max(0, int(settings.llm_max_agents_per_turn))
    if limit <= 0:
        return []

    alive_by_id = {a.id: a for a in sim.agents if a.alive}
    if not alive_by_id:
        return []

    picked: list[AgentState] = []
    seen: set[str] = set()

    # Always try settlement leaders first (theme: power / selection).
    leader_ids = [s.leader_id for s in sim.settlements if s.leader_id]
    rng.shuffle(leader_ids)
    for lid in leader_ids:
        agent = alive_by_id.get(lid)
        if agent is None or agent.id in seen:
            continue
        if agent.energy < 0.15:
            continue
        seen.add(agent.id)
        picked.append(agent)
        if len(picked) >= limit:
            return picked

    scored: list[tuple[int, str, AgentState]] = []
    for agent in alive_by_id.values():
        if agent.id in seen:
            continue
        score = 0
        if "charisma" in agent.traits:
            score += 40
        if "genius" in agent.traits:
            score += 35
        if agent.allegiance.value == "resist":
            score += 10
        if agent.energy < 0.15:
            score -= 50
        scored.append((score, agent.id, agent))
    scored.sort(key=lambda row: (-row[0], row[1]))

    by_region: dict[str, list[AgentState]] = {}
    for score, _, agent in scored:
        if score < 0:
            continue
        key = agent.region_id or "none"
        by_region.setdefault(key, []).append(agent)

    region_keys = list(by_region.keys())
    rng.shuffle(region_keys)
    while len(picked) < limit and any(by_region.values()):
        progress = False
        for key in region_keys:
            bucket = by_region.get(key) or []
            while bucket:
                agent = bucket.pop(0)
                if agent.id in seen:
                    continue
                seen.add(agent.id)
                picked.append(agent)
                progress = True
                break
            if len(picked) >= limit:
                break
        if not progress:
            break

    if len(picked) < limit:
        remainder = [a for _, _, a in scored if a.id not in seen]
        rng.shuffle(remainder)
        for agent in remainder:
            picked.append(agent)
            if len(picked) >= limit:
                break
    return picked[:limit]


def decide_batch(
    sim: SimulationState,
    agents: list[AgentState],
    neighbor_fn,
) -> dict[str, ChosenAction]:
    """Call LLM for selected agents. Returns only successful LLM choices."""
    settings = get_settings()
    provider = (settings.llm_provider or "stub").strip().lower()
    if provider not in {"ollama", "openai"} or not agents:
        return {}

    results: dict[str, ChosenAction] = {}
    workers = max(1, min(int(settings.llm_concurrency), len(agents)))

    def _work(agent: AgentState) -> tuple[str, ChosenAction | None]:
        neighbors = neighbor_fn(sim, agent)
        return agent.id, decide_one(sim, agent, neighbors)

    if workers == 1:
        for agent in agents:
            agent_id, choice = _work(agent)
            if choice is not None:
                results[agent_id] = choice
        return results

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_work, agent) for agent in agents]
        for fut in as_completed(futures):
            try:
                agent_id, choice = fut.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM worker failed: %s", exc)
                continue
            if choice is not None:
                results[agent_id] = choice
    return results


def _clamp01(value: float | str | int | None, default: float = 0.5) -> float:
    """Coerce LLM output to 0..1 (handles numeric strings and labels like 'high')."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        s = value.strip().lower()
        if not s:
            return default
        word_map = {
            "none": 0.0,
            "very_low": 0.1,
            "low": 0.25,
            "medium": 0.5,
            "mid": 0.5,
            "moderate": 0.5,
            "high": 0.75,
            "very_high": 0.9,
            "max": 1.0,
        }
        if s in word_map:
            return word_map[s]
        try:
            return max(0.0, min(1.0, float(s)))
        except ValueError:
            return default
    return default


def build_region_factsheet(sim: SimulationState, turn_events: list[Any] | None = None) -> list[dict[str, Any]]:
    """Compact factual inputs for the regional observer (not the final metrics)."""
    from collections import Counter

    events = turn_events or [e for e in sim.events if e.turn == sim.world.turn]
    rows: list[dict[str, Any]] = []
    for region in sim.world.regions:
        rid = region.id.value
        members = [a for a in sim.agents if a.alive and a.region_id == rid]
        leaders = [
            a
            for a in members
            if any(s.leader_id == a.id for s in sim.settlements)
        ]
        action_counts = Counter()
        shocks: list[str] = []
        for event in events:
            actor_region = None
            if event.actor_id in {rid, region.subregion_id}:
                actor_region = rid
            else:
                agent = next((a for a in sim.agents if a.id == event.actor_id), None)
                if agent and agent.region_id == rid:
                    actor_region = rid
            if actor_region != rid:
                continue
            action_counts[event.action.value] += 1
            if event.action.value in {"disaster", "regime"} or str(event.detail_key).startswith(
                ("disaster_", "epidemic", "weather_", "regime_", "historic_")
            ):
                shocks.append(event.detail_key or event.action.value)
        wealths = [a.wealth for a in members] or [0.0]
        mean_w = sum(wealths) / len(wealths)
        var = sum((w - mean_w) ** 2 for w in wealths) / len(wealths)
        ineq = (var**0.5) / (mean_w + 1e-6)
        rows.append(
            {
                "region_id": rid,
                "subregion_id": region.subregion_id,
                "institution": region.institution.value,
                "tax_rate": round(region.tax_rate, 2),
                "authority": round(region.institution_runtime.authority, 2),
                "resources": round(region.resource_pool, 1),
                "education": round(region.education_level, 2),
                "trade": round(region.trade_openness, 2),
                "climate": region.climate.value,
                "population": len(members),
                "leader_traits": leaders[0].traits if leaders else [],
                "charisma": sum(1 for a in members if "charisma" in a.traits),
                "genius": sum(1 for a in members if "genius" in a.traits),
                "fact_inequality": round(min(2.0, ineq) / 2.0, 3),
                "mean_happiness": round(
                    sum(a.happiness for a in members) / len(members) if members else 0.0, 3
                ),
                "turn_actions": dict(action_counts),
                "shocks": shocks[:4],
                "prev_summary": next(
                    (r.summary for r in sim.region_readings if r.region_id == rid), ""
                ),
            }
        )
    return rows


def heuristic_region_readings(sim: SimulationState, facts: list[dict[str, Any]]) -> list[RegionReading]:
    out: list[RegionReading] = []
    for fact in facts:
        actions = fact.get("turn_actions") or {}
        shocks = fact.get("shocks") or []
        pop = max(1, int(fact.get("population") or 1))
        conflict_n = int(actions.get("conflict", 0))
        coop_n = int(actions.get("cooperate", 0))
        resist_n = int(actions.get("resist", 0))
        disaster_n = len(shocks)
        tension = _clamp01(0.15 + conflict_n / 8 + resist_n / 10 + disaster_n * 0.12)
        prosperity = _clamp01(
            0.25
            + float(fact.get("resources", 0)) / 200
            + float(fact.get("trade", 0)) * 0.3
            + coop_n / 10
            - disaster_n * 0.08
        )
        discontent = _clamp01(
            0.2
            + float(fact.get("tax_rate", 0)) * 0.5
            + float(fact.get("fact_inequality", 0)) * 0.4
            + resist_n / 8
            + disaster_n * 0.1
            - float(fact.get("mean_happiness", 0.5)) * 0.3
        )
        cohesion = _clamp01(0.2 + coop_n / 8 + float(fact.get("mean_happiness", 0.5)) * 0.4 - tension * 0.3)
        if tension >= 0.55 and int(fact.get("charisma", 0)) > 0:
            archetype, traj = "warlord", "war"
        elif discontent >= 0.55:
            archetype, traj = "reformer", "reform"
        elif prosperity >= 0.55 and float(fact.get("trade", 0)) >= 0.45:
            archetype, traj = "merchant", "industry"
        elif float(fact.get("authority", 0.5)) >= 0.6:
            archetype, traj = "bureaucrat", "stagnation"
        elif pop < 20:
            archetype, traj = "explorer", "exodus"
        else:
            archetype, traj = "none", "stagnation"
        if _narrative_lang() == "en":
            inst = fact.get("institution", "democracy")
            inst_label = {"democracy": "democracy", "autocracy": "autocracy", "anarchy": "anarchy"}.get(
                inst, inst
            )
            tax_pct = int(float(fact.get("tax_rate", 0)) * 100)
            shock_txt = f" after {disaster_n} shock(s)" if disaster_n else ""
            conflict_txt = f"{conflict_n} clash(es)" if conflict_n else "little open conflict"
            summary = (
                f"Under {inst_label} at {tax_pct}% tax{shock_txt}, "
                f"{conflict_txt} — a {arch} figure rises toward {traj}."
            )
        else:
            inst = fact.get("institution", "democracy")
            inst_ja = {"democracy": "民主制", "autocracy": "独裁", "anarchy": "無政府"}.get(inst, inst)
            tax_pct = int(float(fact.get("tax_rate", 0)) * 100)
            shock_txt = f"{disaster_n}件の衝撃のあと、" if disaster_n else ""
            conflict_txt = f"争い{conflict_n}件" if conflict_n else "大きな争いは少ない"
            arch = _ARCHETYPE_JA.get(archetype, archetype)
            traj_ja = _TRAJECTORY_JA.get(traj, traj)
            if resist_n >= 2:
                mood = "抵抗が広がり"
            elif discontent >= 0.55:
                mood = "不満が表面化し"
            elif prosperity >= 0.55:
                mood = "豊かさが広がり"
            else:
                mood = "おおむね穏やかな中"
            summary = (
                f"{inst_ja}・税{tax_pct}%の下、{shock_txt}{mood}{conflict_txt}。"
                f"{arch}が台頭し、社会は{traj_ja}へ向かう。"
            )
        out.append(
            RegionReading(
                region_id=fact["region_id"],
                subregion_id=fact.get("subregion_id"),
                tension=tension,
                prosperity=prosperity,
                discontent=discontent,
                cohesion=cohesion,
                rising_archetype=archetype,
                trajectory=traj,
                summary=summary,
                source="heuristic",
            )
        )
    return out


def _parse_one_region_reading(text: str, fact: dict[str, Any]) -> RegionReading | None:
    if not text:
        return None
    raw = text.strip()
    payload: dict[str, Any] | None = None
    start = raw.find("{")
    if start >= 0:
        try:
            payload, _ = json.JSONDecoder().raw_decode(raw[start:])
        except json.JSONDecodeError:
            payload = None
    if not isinstance(payload, dict):
        # Tiny models often truncate nested JSON; recover scalar fields.
        def _num(key: str, default: float = 0.5) -> float:
            match = re.search(rf'"{key}"\s*:\s*(-?[0-9]+(?:\.[0-9]+)?)', raw)
            return float(match.group(1)) if match else default

        def _str(key: str, default: str = "") -> str:
            match = re.search(rf'"{key}"\s*:\s*"([^"]*)"', raw)
            return match.group(1) if match else default

        if '"tension"' not in raw and '"prosperity"' not in raw:
            return None
        payload = {
            "tension": _num("tension"),
            "prosperity": _num("prosperity"),
            "discontent": _num("discontent"),
            "cohesion": _num("cohesion"),
            "rising_archetype": _str("rising_archetype", "none"),
            "trajectory": _str("trajectory", "stagnation"),
            "summary": _str("summary"),
        }
    if "regions" in payload and isinstance(payload["regions"], list) and payload["regions"]:
        row = payload["regions"][0]
        if not isinstance(row, dict):
            return None
    else:
        row = payload
    # Reject echo of the fact sheet (no score keys).
    if "tension" not in row and "prosperity" not in row and "discontent" not in row:
        return None
    archetype = str(row.get("rising_archetype") or "none").strip().lower()
    if archetype not in _ARCHETYPES:
        archetype = "none"
    trajectory = str(row.get("trajectory") or "stagnation").strip().lower()
    if trajectory not in _TRAJECTORIES:
        trajectory = "stagnation"
    summary = str(row.get("summary") or "").strip()
    if summary.startswith("{") or summary.startswith("\\"):
        summary = ""
    if len(summary) > 160:
        summary = summary[:157] + "..."
    return RegionReading(
        region_id=fact["region_id"],
        subregion_id=fact.get("subregion_id"),
        tension=_clamp01(row.get("tension", 0.5)),
        prosperity=_clamp01(row.get("prosperity", 0.5)),
        discontent=_clamp01(row.get("discontent", 0.5)),
        cohesion=_clamp01(row.get("cohesion", 0.5)),
        rising_archetype=archetype,
        trajectory=trajectory,
        summary=summary or (
            f"{fact['region_id']}: {trajectory}"
            if _narrative_lang() == "en"
            else f"{_TRAJECTORY_JA.get(trajectory, trajectory)}の兆し"
        ),
        source="llm",
    )


def heuristic_region_policy(fact: dict[str, Any], reading: RegionReading) -> RegionPolicy:
    tax = float(fact.get("tax_rate", 0.1))
    institution = str(fact.get("institution") or "democracy")
    if reading.discontent >= 0.55 or tax >= 0.3:
        action = ActionType.resist
    elif reading.tension >= 0.55:
        action = ActionType.conflict
    elif reading.prosperity >= 0.6 and reading.cohesion >= 0.45:
        action = ActionType.cooperate
    elif institution != "anarchy" and reading.discontent < 0.35:
        action = ActionType.obey
    elif reading.trajectory == "exodus":
        action = ActionType.migrate
    else:
        action = ActionType.wait
    intensity = _clamp01(0.2 + 0.35 * max(reading.discontent, reading.tension, 1.0 - reading.cohesion))
    return RegionPolicy(
        region_id=fact["region_id"],
        subregion_id=fact.get("subregion_id"),
        action=action,
        intensity=intensity,
        reason=reading.summary
        or (
            f"{institution} stance → {action.value}"
            if _narrative_lang() == "en"
            else f"{institution}の方針 → {action.value}"
        ),
        source=reading.source,
    )


def _parse_group_action(raw: str, payload: dict[str, Any] | None) -> tuple[ActionType, float, str]:
    action = ActionType.wait
    intensity = 0.3
    reason = ""
    row = payload or {}
    action_raw = str(row.get("group_action") or row.get("action") or "").strip().lower()
    try:
        cand = ActionType(action_raw)
        if cand in _ALLOWED_GROUP_ACTIONS:
            action = cand
    except ValueError:
        match = re.search(r'"group_action"\s*:\s*"([^"]+)"', raw or "")
        if match:
            try:
                cand = ActionType(match.group(1).strip().lower())
                if cand in _ALLOWED_GROUP_ACTIONS:
                    action = cand
            except ValueError:
                pass
    if "intensity" in row:
        intensity = _clamp01(row.get("intensity", 0.3))
    else:
        match = re.search(r'"intensity"\s*:\s*(-?[0-9]+(?:\.[0-9]+)?)', raw or "")
        if match:
            intensity = _clamp01(float(match.group(1)))
    reason = str(row.get("reason") or "").strip()
    if not reason:
        match = re.search(r'"reason"\s*:\s*"([^"]*)"', raw or "")
        if match:
            reason = match.group(1).strip()
    if len(reason) > 160:
        reason = reason[:157] + "..."
    return action, intensity, reason


def observe_and_steer_one_region(
    fact: dict[str, Any], heuristic: RegionReading
) -> tuple[RegionReading, RegionPolicy]:
    """One LLM call: semantic reading + institutional/group stance for the region."""
    compact = {
        "id": fact["region_id"],
        "inst": fact["institution"],
        "tax": fact["tax_rate"],
        "auth": fact["authority"],
        "res": fact["resources"],
        "trade": fact["trade"],
        "pop": fact["population"],
        "ineq": fact["fact_inequality"],
        "happy": fact["mean_happiness"],
        "acts": fact["turn_actions"],
        "shocks": fact["shocks"],
        "charisma": fact["charisma"],
    }
    prompt = (
        "You set the STANCE of a whole region (institutions + people as a group), "
        "not one person. Reply flat JSON only with keys "
        "tension,prosperity,discontent,cohesion,rising_archetype,trajectory,summary,"
        "group_action,intensity,reason. "
        "Scores 0..1. "
        "rising_archetype in reformer,warlord,merchant,priest,bureaucrat,explorer,none. "
        "trajectory in war,industry,reform,stagnation,exodus,faith. "
        "group_action in wait,cooperate,conflict,migrate,obey,resist. "
        "intensity 0..1 = how strongly the group enacts group_action. "
        f"{_narrative_instruction()}"
        "Keep enum values (rising_archetype, trajectory, group_action) in English as listed.\n"
        f"Data:{json.dumps(compact, ensure_ascii=False)}"
    )
    heuristic_policy = heuristic_region_policy(fact, heuristic)
    try:
        text = complete_decision_text(prompt, num_predict=180)
    except Exception as exc:  # noqa: BLE001
        logger.info("region steer failed for %s: %s", fact.get("region_id"), exc)
        return heuristic, heuristic_policy

    reading = _parse_one_region_reading(text, fact) or heuristic
    if reading is not heuristic and reading.summary.lower() in {
        "cause→effect",
        "cause->effect",
        "short cause→effect",
    }:
        if _narrative_lang() == "en":
            reading.summary = (
                f"{fact['region_id']}: tax={fact['tax_rate']} shocks={len(fact.get('shocks') or [])} "
                f"→ {reading.rising_archetype}/{reading.trajectory}"
            )
        else:
            arch = _ARCHETYPE_JA.get(reading.rising_archetype, reading.rising_archetype)
            traj_ja = _TRAJECTORY_JA.get(reading.trajectory, reading.trajectory)
            reading.summary = (
                f"税{fact['tax_rate']}・衝撃{len(fact.get('shocks') or [])}件 "
                f"→ {arch}が台頭、軌道は{traj_ja}"
            )

    payload: dict[str, Any] | None = None
    start = (text or "").find("{")
    if start >= 0:
        try:
            payload, _ = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            payload = None
    action, intensity, reason = _parse_group_action(text or "", payload if isinstance(payload, dict) else None)
    if action == ActionType.wait and not reason:
        policy = heuristic_region_policy(fact, reading)
        policy.source = reading.source
        return reading, policy
    policy = RegionPolicy(
        region_id=fact["region_id"],
        subregion_id=fact.get("subregion_id"),
        action=action,
        intensity=intensity,
        reason=reason or reading.summary or (
            f"group {action.value}" if _narrative_lang() == "en" else f"集団の方針は{action.value}"
        ),
        source="llm",
    )
    if reading.source != "llm":
        reading = RegionReading(
            region_id=reading.region_id,
            subregion_id=reading.subregion_id,
            tension=reading.tension,
            prosperity=reading.prosperity,
            discontent=reading.discontent,
            cohesion=reading.cohesion,
            rising_archetype=reading.rising_archetype,
            trajectory=reading.trajectory,
            summary=reading.summary,
            source="llm",
        )
    return reading, policy


def observe_and_steer_regions(
    sim: SimulationState, turn_events: list[Any] | None = None
) -> tuple[list[RegionReading], list[RegionPolicy], str]:
    """Per-region observation + group stance. Replaces per-agent LLM decisions."""
    facts = build_region_factsheet(sim, turn_events)
    if not facts:
        return [], [], ""
    fallback = heuristic_region_readings(sim, facts)
    settings = get_settings()
    provider = (settings.llm_provider or "stub").strip().lower()
    if provider not in {"ollama", "openai"}:
        policies = [heuristic_region_policy(f, h) for f, h in zip(facts, fallback)]
        if _narrative_lang() == "en":
            parts = []
            for reading in fallback:
                if reading.summary:
                    parts.append(f"{reading.region_id}: {reading.summary}")
            stub = "; ".join(parts[:3]) if parts else "Heuristic group stance (LLM stub)."
        else:
            parts = []
            for reading in fallback:
                if reading.summary:
                    geo = {
                        "africa": "アフリカ",
                        "europe": "欧州",
                        "asia": "アジア",
                        "america": "米州",
                        "oceania": "オセアニア",
                    }.get(reading.region_id, reading.region_id)
                    parts.append(f"{geo}は{reading.summary}")
            stub = " ".join(parts[:2]) if parts else "各地域はヒューリスティックで読み取られた。"
        return fallback, policies, stub

    readings: list[RegionReading] = []
    policies: list[RegionPolicy] = []
    for fact, heuristic in zip(facts, fallback):
        reading, policy = observe_and_steer_one_region(fact, heuristic)
        readings.append(reading)
        policies.append(policy)

    llm_hits = sum(1 for r in readings if r.source == "llm")
    reading_by_id = {r.region_id: r for r in readings}
    parts = [
        f"{p.region_id}:{p.action.value}/{(reading_by_id.get(p.region_id).rising_archetype if reading_by_id.get(p.region_id) else 'none')}"
        for p in policies
    ]
    if _narrative_lang() == "en":
        world_summary = (
            f"Group LLM steered {llm_hits}/{len(readings)} regions — " + "; ".join(parts)
            if llm_hits
            else "Heuristic group stance (LLM unavailable)."
        )
    else:
        world_summary = (
            f"集団LLMが {llm_hits}/{len(readings)} 地域を誘導 — " + "; ".join(parts)
            if llm_hits
            else "ヒューリスティックの集団方針（LLM利用不可）。"
        )
    if len(world_summary) > 200:
        world_summary = world_summary[:197] + "..."
    return readings, policies, world_summary


def observe_regions(sim: SimulationState, turn_events: list[Any] | None = None) -> tuple[list[RegionReading], str]:
    readings, _policies, world_summary = observe_and_steer_regions(sim, turn_events)
    return readings, world_summary
