from __future__ import annotations

import math
import random
from collections import defaultdict

from simulation.continents import CONTINENT_PRESETS, SUBREGION_CENTERS, resolve_preset, resolve_subregion
from simulation.llm import observe_and_steer_regions
from config import get_settings
from simulation.shocks import apply_epidemics, apply_historic_quakes, apply_weather_shocks
from simulation.models import (
    ActionType,
    AgentState,
    Allegiance,
    ChosenAction,
    ClimateType,
    EventRecord,
    GeographyType,
    HistoryRecord,
    InstitutionType,
    InstitutionState,
    LandformType,
    MetricsSnapshot,
    RegionMetricsSnapshot,
    RegionPolicy,
    RegionReading,
    Personality,
    Position,
    RegionParams,
    RegionState,
    RelationshipState,
    ReligionType,
    SettlementState,
    SimulationState,
    WorldParams,
    WorldState,
    YEARS_PER_TURN,
    MAX_CALENDAR_YEAR,
    resolve_theater_and_landform,
)
from simulation.terrain import biome_at, generate_terrain, random_land_position, snap_to_land


SETTLEMENT_DISTANCE = 22.0
SETTLEMENT_MIN_SIZE = 2
POPULATION_MIN = 1000
POPULATION_MAX = 10000
ENERGY_WAIT_THRESHOLD = 0.15
CROSS_CONTINENT_CHANCE = 0.015
COHORT_MIGRATE_CHANCE = 0.20
MAX_BIRTHS_PER_REGION = 24
MAX_MEMORY = 10
BIRTH_MIN_WEALTH = 4.0
BIRTH_MIN_HAPPINESS = 0.35
BIRTH_COST = 1.5
CHARISMA_CHANCE = 0.10
GENIUS_CHANCE = 0.08
TRAIT_INHERIT_BONUS = 0.18
BIRTH_AGE_MIN = 16
BIRTH_AGE_MAX = 55
TRAIT_GAIN_CHANCE = 0.018
TRAIT_LOSE_CHANCE = 0.03
ACTION_PRIORITY = {
    ActionType.resist: 0,
    ActionType.obey: 0,
    ActionType.conflict: 1,
    ActionType.cooperate: 2,
    ActionType.migrate: 3,
    ActionType.wait: 4,
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def pair_key(a_id: str, b_id: str) -> tuple[str, str]:
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def roll_traits(
    rng: random.Random,
    parent: AgentState | None = None,
    trait_rate: float | None = None,
) -> list[str]:
    traits: list[str] = []
    base_c = CHARISMA_CHANCE if trait_rate is None else float(trait_rate)
    base_g = GENIUS_CHANCE if trait_rate is None else float(trait_rate) * 0.8
    charisma_p = base_c + (TRAIT_INHERIT_BONUS if parent and "charisma" in parent.traits else 0)
    genius_p = base_g + (TRAIT_INHERIT_BONUS if parent and "genius" in parent.traits else 0)
    if rng.random() < charisma_p:
        traits.append("charisma")
    if rng.random() < genius_p:
        traits.append("genius")
    return traits


def leadership_score(agent: AgentState, rng: random.Random | None = None) -> float:
    score = agent.wealth + agent.personality.ambition * 22
    if "charisma" in agent.traits:
        score += 18
    if "genius" in agent.traits:
        score += 10
    score -= max(0, agent.age - 48) * 0.9
    if rng is not None:
        score += rng.uniform(0, 7)
    return score


def _region_seed(base: int, region_id: str) -> int:
    return (base + sum((i + 1) * ord(ch) for i, ch in enumerate(region_id))) % 2_147_483_647


def _build_region(params: RegionParams, seed: int) -> RegionState:
    preset = resolve_preset(params.id, params.subregion_id)
    landform = preset["landform"]
    climate = preset["climate"]
    resource_pool = float(preset["resource_pool"])
    disaster_frequency = float(preset["disaster_frequency"])
    sanitation = float(preset.get("sanitation", 0.5))
    terrain = generate_terrain(landform, climate, _region_seed(seed, params.subregion_id or params.id.value))
    return RegionState(
        id=params.id,
        subregion_id=params.subregion_id,
        landform=landform,
        climate=climate,
        disaster_frequency=disaster_frequency,
        sanitation=sanitation,
        resource_pool=resource_pool,
        education_level=params.education_level,
        tax_rate=params.tax_rate,
        institution=params.institution,
        religion=params.religion,
        trade_openness=params.trade_openness,
        initial_values=params.initial_values,
        terrain=terrain,
        institution_runtime=InstitutionState(
            authority=0.4 + 0.3 * params.initial_values.authority_acceptance
        ),
        trait_rate=params.trait_rate,
        welfare_rate=params.welfare_rate,
    )


def _region_key(agent: AgentState) -> str:
    return agent.subregion_id or agent.region_id or "lone"


def agent_region(sim: SimulationState, agent: AgentState) -> RegionState | None:
    if not sim.world.regions:
        return None
    sid = agent.subregion_id
    rid = agent.region_id
    if sid:
        for region in sim.world.regions:
            if region.subregion_id == sid:
                return region
    if rid:
        for region in sim.world.regions:
            if region.id.value == rid and region.subregion_id == sid:
                return region
        for region in sim.world.regions:
            if region.id.value == rid:
                return region
    return sim.world.regions[0]


def agents_in_region(sim: SimulationState, region: RegionState) -> list[AgentState]:
    sid = region.subregion_id
    rid = region.id.value
    out: list[AgentState] = []
    for agent in sim.agents:
        if not agent.alive:
            continue
        if sid:
            if agent.subregion_id == sid:
                out.append(agent)
        elif agent.region_id == rid:
            out.append(agent)
    return out


def _cohort_key(agent: AgentState) -> str:
    return agent.settlement_id or _region_key(agent) or agent.id


def region_terrain(sim: SimulationState, agent: AgentState):
    region = agent_region(sim, agent)
    return region.terrain if region else sim.world.terrain


def create_simulation(sim_id: str, params: WorldParams) -> SimulationState:
    rng = random.Random(params.seed)
    region_params = list(params.regions)
    if not region_params:
        theater, landform = resolve_theater_and_landform(params.geography, params.landform)
        region_params = [
            RegionParams(
                id=theater if theater in CONTINENT_PRESETS else GeographyType.asia,
                subregion_id=resolve_subregion(
                    theater if theater in CONTINENT_PRESETS else GeographyType.asia,
                    None,
                ),
                population=max(POPULATION_MIN, min(POPULATION_MAX, params.population)),
                institution=params.institution,
                tax_rate=params.tax_rate,
                education_level=params.education_level,
                religion=params.religion,
                initial_values=params.initial_values,
            )
        ]
    regions = [_build_region(item, params.seed) for item in region_params]
    agents: list[AgentState] = []
    idx = 0
    for spec, region in zip(region_params, regions):
        # Several camps across the region so individuals read as a scattered band,
        # not one tight blob. Nearby camps still merge via SETTLEMENT_DISTANCE.
        n_camps = max(4, min(20, spec.population // 60))
        homes = [
            random_land_position(region.terrain, rng, region.landform, region.climate)
            for _ in range(n_camps)
        ]
        per_camp = max(1, spec.population // n_camps)
        local_jitter = min(7.0, 2.8 + per_camp * 0.012)
        for _ in range(spec.population):
            idx += 1
            coop = clamp(spec.initial_values.cooperation + rng.uniform(-0.2, 0.2))
            aggr = clamp(0.4 + rng.uniform(-0.25, 0.25))
            ambi = clamp(spec.initial_values.ambition + rng.uniform(-0.2, 0.2))
            traits = roll_traits(rng, trait_rate=region.trait_rate)
            if "charisma" in traits:
                ambi = max(ambi, 0.68)
            spread = 4.0 + 28.0 * spec.initial_values.inequality
            wealth = rng.uniform(max(2.0, 14.0 - spread / 2), 14.0 + spread / 2)
            if "genius" in traits:
                wealth += 4
            home = homes[rng.randrange(len(homes))]
            # Mild radial bias so camps look organic rather than a hard square.
            angle = rng.uniform(0, 2 * math.pi)
            radius = local_jitter * (rng.random() ** 0.55)
            pos = snap_to_land(
                region.terrain,
                home.x + math.cos(angle) * radius,
                home.y + math.sin(angle) * radius,
            )
            agents.append(
                AgentState(
                    id=f"a{idx}",
                    name=f"a{idx}",
                    position=pos,
                    wealth=wealth,
                    energy=clamp(0.7 + rng.uniform(-0.2, 0.2)),
                    happiness=clamp(0.5 + rng.uniform(-0.15, 0.15)),
                    personality=Personality(cooperation=coop, aggression=aggr, ambition=ambi),
                    goal="survive and grow",
                    traits=traits,
                    age=rng.randint(16, 52),
                    region_id=region.id.value,
                    subregion_id=region.subregion_id,
                )
            )

    primary = regions[0]
    world = WorldState(
        turn=0,
        seed=params.seed,
        initial_population=len(agents),
        initial_total_wealth=sum(a.wealth for a in agents),
        population_cap=min(
            max(len(regions), 1) * POPULATION_MAX,
            max(len(agents), int(len(agents) * 1.4)),
        ),
        resource_pool=sum(r.resource_pool for r in regions),
        education_level=sum(r.education_level for r in regions) / len(regions),
        tax_rate=sum(r.tax_rate for r in regions) / len(regions),
        institution=primary.institution,
        start_year=params.start_year,
        years_per_turn=YEARS_PER_TURN,
        geography=GeographyType.world,
        landform=primary.landform,
        climate=primary.climate,
        disaster_frequency=sum(r.disaster_frequency for r in regions) / len(regions),
        religion=primary.religion,
        terrain=primary.terrain,
        initial_values=primary.initial_values,
        institution_runtime=InstitutionState(
            authority=sum(r.institution_runtime.authority for r in regions) / len(regions)
        ),
        regions=regions,
    )

    sim = SimulationState(
        id=sim_id,
        world=world,
        agents=agents,
        relationships=[],
        settlements=[],
    )
    recompute_settlements(sim)
    sim.last_metrics = compute_metrics(sim, cooperate_successes=0, action_count=0, micro_events=[])
    return sim


def get_relationship(sim: SimulationState, a_id: str, b_id: str) -> RelationshipState:
    key = pair_key(a_id, b_id)
    for rel in sim.relationships:
        if pair_key(rel.a_id, rel.b_id) == key:
            return rel
    rel = RelationshipState(a_id=key[0], b_id=key[1])
    sim.relationships.append(rel)
    return rel


def distance(a: Position, b: Position) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def nearest_other(sim: SimulationState, agent: AgentState) -> AgentState | None:
    others = [
        a
        for a in sim.agents
        if a.alive and a.id != agent.id and _region_key(a) == _region_key(agent)
    ]
    if not others:
        return None
    return min(others, key=lambda o: distance(agent.position, o.position))


def nearby_with_trust(
    sim: SimulationState, agent: AgentState, limit: int = 5
) -> list[tuple[AgentState, float, float]]:
    others = [
        a
        for a in sim.agents
        if a.alive and a.id != agent.id and _region_key(a) == _region_key(agent)
    ]
    ranked: list[tuple[AgentState, float, float]] = []
    for other in others:
        dist = distance(agent.position, other.position)
        trust = get_relationship(sim, agent.id, other.id).trust
        ranked.append((other, trust, dist))
    ranked.sort(key=lambda row: row[2])
    return ranked[:limit]


def _attach_migrate_coords(agent: AgentState, choice: ChosenAction, rng: random.Random) -> ChosenAction:
    if choice.action != ActionType.migrate:
        return choice
    if choice.reason.startswith("migrate:") or choice.reason.startswith("migrate_cross:"):
        return choice
    dx, dy = rng.uniform(-12, 12), rng.uniform(-12, 12)
    choice.reason = f"migrate:{agent.position.x + dx:.1f},{agent.position.y + dy:.1f}"
    return choice


def _choice_extra(choice: ChosenAction) -> dict[str, str]:
    extra: dict[str, str] = {}
    if choice.source == "llm":
        extra["decide"] = "llm"
        text = (choice.rationale or choice.reason or "").strip()
        if text and not text.startswith("migrate"):
            extra["reason"] = text[:180]
    return extra


def heuristic_decide(sim: SimulationState, agent: AgentState, rng: random.Random) -> ChosenAction:
    if agent.energy < ENERGY_WAIT_THRESHOLD:
        return ChosenAction(agent_id=agent.id, action=ActionType.wait, reason="low energy")

    target = nearest_other(sim, agent)
    p = agent.personality
    roll = rng.random()

    if target is not None:
        rel = get_relationship(sim, agent.id, target.id)
        if p.aggression > 0.65 and rel.trust < 0 and roll < 0.35:
            return ChosenAction(
                agent_id=agent.id,
                action=ActionType.conflict,
                target_id=target.id,
                reason="aggressive heuristic",
            )
        if p.cooperation > 0.45 and roll < 0.45 + 0.2 * rel.trust:
            return ChosenAction(
                agent_id=agent.id,
                action=ActionType.cooperate,
                target_id=target.id,
                reason="cooperative heuristic",
            )

    region = agent_region(sim, agent)
    institution = region.institution if region else sim.world.institution
    religion = region.religion if region else sim.world.religion
    authority_acceptance = (
        region.initial_values.authority_acceptance
        if region
        else sim.world.initial_values.authority_acceptance
    )
    if institution.value != "anarchy":
        piety = {
            ReligionType.folk: 0.08,
            ReligionType.polytheism: 0.12,
            ReligionType.monotheism: 0.18,
            ReligionType.organized: 0.18,
            ReligionType.secular: -0.04,
        }.get(religion, 0.08)
        if p.ambition < 0.4 and roll < 0.25 + authority_acceptance * 0.2 + piety:
            return ChosenAction(agent_id=agent.id, action=ActionType.obey, reason="obey institution")
        if p.ambition > 0.7 and roll < max(0.08, 0.2 - piety):
            return ChosenAction(agent_id=agent.id, action=ActionType.resist, reason="resist institution")

    if p.ambition > 0.55 and roll < 0.25:
        dx = rng.uniform(-12, 12)
        dy = rng.uniform(-12, 12)
        return ChosenAction(
            agent_id=agent.id,
            action=ActionType.migrate,
            reason=f"migrate:{agent.position.x + dx:.1f},{agent.position.y + dy:.1f}",
        )

    return ChosenAction(agent_id=agent.id, action=ActionType.wait, reason="default wait")


def _cohere_region_migration(
    sim: SimulationState, choices: list[ChosenAction], rng: random.Random
) -> list[ChosenAction]:
    """集落（なければ亜地域）ごとに同じ変位で移す。大陸をまたぐ移動は例外。

    既に行動が付いたエージェントだけを対象にする（集団サンプル方針でも全人口へ拡散しない）。
    LLM / 集団方針が選んだ行動は上書きしない。
    """
    by_id = {c.agent_id: c for c in choices}
    llm_locked = {c.agent_id for c in choices if c.source == "llm"}
    by_cohort: dict[str, list[AgentState]] = defaultdict(list)
    agents_by_id = {a.id: a for a in sim.agents if a.alive}
    for agent_id in by_id:
        agent = agents_by_id.get(agent_id)
        if agent is not None:
            by_cohort[_cohort_key(agent)].append(agent)
    other_regions = sim.world.regions
    for members in by_cohort.values():
        if not members:
            continue
        cohort_members = [m for m in members if m.id not in llm_locked]
        if not cohort_members:
            continue
        migrating = any(by_id[m.id].action == ActionType.migrate for m in cohort_members)
        mean_e = sum(m.energy for m in cohort_members) / len(cohort_members)
        if not migrating and mean_e > 0.42 and rng.random() < COHORT_MIGRATE_CHANCE:
            migrating = True
        if not migrating:
            continue
        dest = None
        if other_regions and rng.random() < CROSS_CONTINENT_CHANCE:
            candidates = [
                r
                for r in other_regions
                if r.id.value != cohort_members[0].region_id
            ]
            if candidates:
                dest = rng.choice(candidates)
        if dest is not None:
            landing = random_land_position(dest.terrain, rng, dest.landform, dest.climate)
            sid = dest.subregion_id or dest.id.value
            for member in cohort_members:
                jx, jy = rng.uniform(-4, 4), rng.uniform(-4, 4)
                by_id[member.id] = ChosenAction(
                    agent_id=member.id,
                    action=ActionType.migrate,
                    reason=(
                        f"migrate_cross:{dest.id.value}:{sid}:"
                        f"{landing.x + jx:.1f},{landing.y + jy:.1f}"
                    ),
                )
            continue
        dx, dy = rng.uniform(-7, 7), rng.uniform(-7, 7)
        for member in cohort_members:
            by_id[member.id] = ChosenAction(
                agent_id=member.id,
                action=ActionType.migrate,
                reason=f"migrate:{member.position.x + dx:.1f},{member.position.y + dy:.1f}",
            )
    return [by_id[a.id] for a in sim.agents if a.alive and a.id in by_id]


def _pick_group_actors(
    sim: SimulationState,
    members: list[AgentState],
    sample_size: int,
    rng: random.Random,
) -> list[AgentState]:
    if not members or sample_size <= 0:
        return []
    leaders = {
        s.leader_id
        for s in sim.settlements
        if s.leader_id and any(m.id == s.leader_id for m in members)
    }
    scored: list[tuple[int, str, AgentState]] = []
    for agent in members:
        score = 0
        if agent.id in leaders:
            score += 100
        if "charisma" in agent.traits:
            score += 40
        if "genius" in agent.traits:
            score += 30
        scored.append((score, agent.id, agent))
    scored.sort(key=lambda row: (-row[0], row[1]))
    picked: list[AgentState] = []
    seen: set[str] = set()
    for _, _, agent in scored:
        if agent.id in seen:
            continue
        seen.add(agent.id)
        picked.append(agent)
        if len(picked) >= sample_size:
            return picked
    return picked


def _policy_target(sim: SimulationState, agent: AgentState, action: ActionType, rng: random.Random) -> str | None:
    if action not in {ActionType.cooperate, ActionType.conflict}:
        return None
    # Prefer another region's leader, else nearest local peer.
    other_leaders = [
        a
        for a in sim.agents
        if a.alive and a.region_id != agent.region_id and any(s.leader_id == a.id for s in sim.settlements)
    ]
    if other_leaders and (action == ActionType.conflict or rng.random() < 0.55):
        return rng.choice(other_leaders).id
    peer = nearest_other(sim, agent)
    return peer.id if peer else None


def decide_actions(sim: SimulationState, rng: random.Random) -> list[ChosenAction]:
    """Enact region/institution stances on a small sample — not per-person LLM."""
    settings = get_settings()
    sample_n = max(4, int(settings.llm_group_sample_per_region))
    policies = {p.region_id: p for p in sim.region_policies}
    choices: list[ChosenAction] = []

    if sim.world.regions:
        region_iter = list(sim.world.regions)
    else:
        region_iter = []

    for region in region_iter:
        rid = region.id.value
        policy = policies.get(rid)
        if policy is None:
            policy = RegionPolicy(region_id=rid, subregion_id=region.subregion_id, action=ActionType.wait)
        members = [a for a in sim.agents if a.alive and a.region_id == rid]
        actors = _pick_group_actors(sim, members, sample_n, rng)
        enact_n = max(1, int(round(len(actors) * clamp(policy.intensity, 0.15, 1.0)))) if actors else 0
        for idx, agent in enumerate(actors):
            if idx >= enact_n or policy.action == ActionType.wait:
                choices.append(
                    ChosenAction(
                        agent_id=agent.id,
                        action=ActionType.wait,
                        reason="group hold",
                        source=policy.source,
                        rationale=policy.reason,
                    )
                )
                continue
            target_id = _policy_target(sim, agent, policy.action, rng)
            choice = ChosenAction(
                agent_id=agent.id,
                action=policy.action,
                target_id=target_id,
                reason=policy.reason or f"group:{policy.action.value}",
                source=policy.source,
                rationale=policy.reason,
            )
            choices.append(_attach_migrate_coords(agent, choice, rng))

    # Group stance already picked who moves; do not expand/override via cohort heuristics.
    return choices


def resolve_actions(
    sim: SimulationState, choices: list[ChosenAction], rng: random.Random
) -> tuple[int, int, list[EventRecord]]:
    agents = {a.id: a for a in sim.agents}
    events: list[EventRecord] = []
    cooperate_successes = 0

    # conflict が同一ペアで出たら cooperate を無効化
    conflict_pairs: set[tuple[str, str]] = set()
    for c in choices:
        if c.action == ActionType.conflict and c.target_id:
            conflict_pairs.add(pair_key(c.agent_id, c.target_id))

    normalized: list[ChosenAction] = []
    for c in choices:
        if (
            c.action == ActionType.cooperate
            and c.target_id
            and pair_key(c.agent_id, c.target_id) in conflict_pairs
        ):
            normalized.append(
                ChosenAction(agent_id=c.agent_id, action=ActionType.wait, reason="conflict overrides cooperate")
            )
        else:
            normalized.append(c)

    normalized.sort(key=lambda c: (ACTION_PRIORITY[c.action], c.agent_id))

    for choice in normalized:
        actor = agents.get(choice.agent_id)
        if actor is None or not actor.alive:
            continue

        action = choice.action
        if actor.energy < ENERGY_WAIT_THRESHOLD and action != ActionType.wait:
            action = ActionType.wait

        if action == ActionType.wait:
            before = actor.energy
            actor.energy = clamp(actor.energy + 0.1)
            reason = choice.reason or "wait"
            detail_key = "wait"
            if "low energy" in reason:
                detail_key = "wait_low_energy"
            elif "conflict overrides" in reason:
                detail_key = "conflict_overrides_cooperate"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.wait,
                    detail_key=detail_key,
                    detail=reason,
                    deltas={"energy": actor.energy - before},
                    extra=_choice_extra(choice),
                )
            )
            continue

        if action == ActionType.cooperate:
            target = agents.get(choice.target_id or "")
            if target is None or not target.alive:
                actor.energy = clamp(actor.energy + 0.05)
                events.append(
                    EventRecord(
                        turn=sim.world.turn,
                        actor_id=actor.id,
                        action=ActionType.wait,
                        detail_key="cooperate_missing_target",
                        detail="cooperate fallback: missing target",
                        extra=_choice_extra(choice),
                    )
                )
                continue

            rel = get_relationship(sim, actor.id, target.id)
            region = agent_region(sim, actor)
            education = region.education_level if region else sim.world.education_level
            pool = region.resource_pool if region else sim.world.resource_pool
            max_wealth = max(a.wealth for a in sim.agents) or 1.0
            p = clamp(
                0.5
                + 0.25 * rel.trust
                + 0.20 * education
                + 0.15 * ((actor.personality.cooperation + target.personality.cooperation) / 2)
                - 0.10 * abs(actor.wealth - target.wealth) / max_wealth
            )
            success = rng.random() < p
            if success:
                gain = min(3.0, pool * 0.02 + 1.0)
                if region:
                    region.resource_pool = max(0.0, region.resource_pool - gain * 2)
                else:
                    sim.world.resource_pool = max(0.0, sim.world.resource_pool - gain * 2)
                actor.wealth += gain
                target.wealth += gain
                rel.trust = clamp(rel.trust + 0.1, -1, 1)
                rel.affinity = clamp(rel.affinity + 0.05, -1, 1)
                actor.happiness = clamp(actor.happiness + 0.05)
                target.happiness = clamp(target.happiness + 0.05)
                cooperate_successes += 1
                detail_key = "cooperate_success"
                detail = f"cooperate success with {target.id}"
            else:
                actor.energy = clamp(actor.energy - 0.1)
                target.energy = clamp(target.energy - 0.1)
                rel.trust = clamp(rel.trust - 0.05, -1, 1)
                detail_key = "cooperate_failed"
                detail = f"cooperate failed with {target.id}"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.cooperate,
                    target_id=target.id,
                    success=success,
                    detail_key=detail_key,
                    detail=detail,
                    extra=_choice_extra(choice),
                )
            )
            _remember(actor, detail)
            _remember(target, detail)
            continue

        if action == ActionType.conflict:
            target = agents.get(choice.target_id or "")
            if target is None or not target.alive:
                events.append(
                    EventRecord(
                        turn=sim.world.turn,
                        actor_id=actor.id,
                        action=ActionType.wait,
                        detail_key="conflict_missing_target",
                        detail="conflict fallback: missing target",
                        extra=_choice_extra(choice),
                    )
                )
                continue

            def power(x: AgentState) -> float:
                return x.wealth * 0.4 + x.energy * 0.3 + x.personality.aggression * 0.3 + rng.random() * 0.2

            actor_power = power(actor)
            target_power = power(target)
            winner, loser = (actor, target) if actor_power >= target_power else (target, actor)
            stolen = min(4.0, loser.wealth * 0.2)
            winner.wealth += stolen
            loser.wealth = max(0.0, loser.wealth - stolen)
            winner.energy = clamp(winner.energy - 0.15)
            loser.energy = clamp(loser.energy - 0.2)
            loser.happiness = clamp(loser.happiness - 0.1)
            rel = get_relationship(sim, actor.id, target.id)
            rel.trust = clamp(rel.trust - 0.2, -1, 1)
            won = winner.id == actor.id
            detail_key = "conflict_win" if won else "conflict_lose"
            detail = f"conflict: {winner.id} beat {loser.id}"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.conflict,
                    target_id=target.id,
                    success=won,
                    detail_key=detail_key,
                    detail=detail,
                    deltas={"stolen": stolen},
                    extra=_choice_extra(choice),
                )
            )
            _remember(actor, detail)
            _remember(target, detail)
            continue

        if action == ActionType.migrate:
            # reason に migrate:x,y があれば使う。なければランダム近傍。
            nx, ny = actor.position.x, actor.position.y
            if choice.reason.startswith("migrate_cross:"):
                try:
                    _, rest = choice.reason.split(":", 1)
                    dest_id, dest_sub, coords = rest.split(":", 2)
                    nx_s, ny_s = coords.split(",")
                    nx, ny = float(nx_s), float(ny_s)
                    actor.region_id = dest_id
                    actor.subregion_id = dest_sub
                    actor.settlement_id = None
                except ValueError:
                    nx += rng.uniform(-10, 10)
                    ny += rng.uniform(-10, 10)
            elif choice.reason.startswith("migrate:"):
                try:
                    coords = choice.reason.split(":", 1)[1]
                    nx_s, ny_s = coords.split(",")
                    nx, ny = float(nx_s), float(ny_s)
                except ValueError:
                    nx += rng.uniform(-10, 10)
                    ny += rng.uniform(-10, 10)
            else:
                nx += rng.uniform(-10, 10)
                ny += rng.uniform(-10, 10)
            actor.position = snap_to_land(region_terrain(sim, actor), nx, ny)
            cost = 0.08
            region = agent_region(sim, actor)
            if (region.landform if region else sim.world.landform) == LandformType.island:
                cost += 0.04
            if (region.climate if region else sim.world.climate) == ClimateType.cold:
                cost += 0.03
            biome = biome_at(region_terrain(sim, actor), actor.position.x, actor.position.y)
            if biome in ("marsh", "mountain", "tundra"):
                cost += 0.05
            actor.energy = clamp(actor.energy - cost)
            detail = f"migrated to ({actor.position.x:.1f},{actor.position.y:.1f})"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.migrate,
                    detail_key="migrate",
                    detail=detail,
                    deltas={"x": actor.position.x, "y": actor.position.y},
                    extra=_choice_extra(choice),
                )
            )
            _remember(actor, detail)
            continue

        if action == ActionType.obey:
            region = agent_region(sim, actor)
            tax_rate = region.tax_rate if region else sim.world.tax_rate
            runtime = region.institution_runtime if region else sim.world.institution_runtime
            pay = actor.wealth * tax_rate
            actor.wealth = max(0.0, actor.wealth - pay)
            runtime.treasury += pay
            actor.allegiance = Allegiance.obey
            runtime.authority = clamp(runtime.authority + 0.02)
            if tax_rate > 0.2:
                actor.happiness = clamp(actor.happiness - 0.02)
            detail = f"obeyed, paid {pay:.2f}"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.obey,
                    detail_key="obey",
                    detail=detail,
                    deltas={"tax": pay},
                    extra=_choice_extra(choice),
                )
            )
            _remember(actor, detail)
            continue

        if action == ActionType.resist:
            region = agent_region(sim, actor)
            runtime = region.institution_runtime if region else sim.world.institution_runtime
            actor.allegiance = Allegiance.resist
            runtime.authority = clamp(runtime.authority - 0.03)
            same = [
                a
                for a in sim.agents
                if a.alive and _region_key(a) == _region_key(actor)
            ]
            resist_count = sum(1 for a in same if a.allegiance == Allegiance.resist)
            if resist_count >= max(2, len(same) // 3):
                actor.happiness = clamp(actor.happiness + 0.02)
            else:
                actor.happiness = clamp(actor.happiness - 0.05)
            detail = "resisted institution"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.resist,
                    detail_key="resist",
                    detail=detail,
                    extra=_choice_extra(choice),
                )
            )
            _remember(actor, detail)

    return cooperate_successes, len(normalized), events


def _remember(agent: AgentState, text: str) -> None:
    agent.memory.append(text)
    if len(agent.memory) > MAX_MEMORY:
        agent.memory = agent.memory[-MAX_MEMORY:]


def _next_agent_index(sim: SimulationState) -> int:
    nums: list[int] = []
    for agent in sim.agents:
        if agent.id.startswith("a"):
            try:
                nums.append(int(agent.id[1:]))
            except ValueError:
                continue
    return (max(nums) if nums else 0) + 1


def apply_births(sim: SimulationState, rng: random.Random) -> None:
    alive = [a for a in sim.agents if a.alive]
    if len(alive) >= sim.world.population_cap:
        return
    by_region: dict[str, list[AgentState]] = defaultdict(list)
    for agent in alive:
        by_region[_region_key(agent)].append(agent)
    for members in by_region.values():
        if len(alive) >= sim.world.population_cap:
            return
        if len(members) >= POPULATION_MAX:
            continue
        eligible = [
            a
            for a in members
            if a.wealth >= BIRTH_MIN_WEALTH
            and a.happiness >= BIRTH_MIN_HAPPINESS
            and a.energy > 0.18
            and BIRTH_AGE_MIN <= a.age <= BIRTH_AGE_MAX
        ]
        if not eligible:
            continue
        mean_h = sum(a.happiness for a in members) / len(members)
        parent_p = 0.32 + 0.22 * mean_h + 0.08 * sim.world.education_level
        born = 0
        rng.shuffle(eligible)
        for parent in eligible:
            if born >= MAX_BIRTHS_PER_REGION:
                break
            if len(alive) >= sim.world.population_cap or len(members) + born >= POPULATION_MAX:
                break
            if rng.random() >= parent_p:
                continue
            child = _spawn_child(sim, parent, rng)
            if child is None:
                continue
            alive.append(child)
            members.append(child)
            born += 1


def _spawn_child(sim: SimulationState, parent: AgentState, rng: random.Random) -> AgentState | None:
    idx = _next_agent_index(sim)
    child_id = f"a{idx}"
    home = agent_region(sim, parent)
    traits = roll_traits(rng, parent, home.trait_rate if home else None)
    ambi = clamp(parent.personality.ambition + rng.uniform(-0.12, 0.12))
    if "charisma" in traits:
        ambi = max(ambi, 0.68)
    wealth = 6.0 + rng.uniform(0, 3)
    if "genius" in traits:
        wealth += 3
    child = AgentState(
        id=child_id,
        name=child_id,
        position=snap_to_land(
            region_terrain(sim, parent),
            parent.position.x + rng.uniform(-6, 6),
            parent.position.y + rng.uniform(-6, 6),
        ),
        wealth=wealth,
        energy=clamp(0.65 + rng.uniform(-0.1, 0.1)),
        happiness=clamp(0.55 + rng.uniform(-0.08, 0.08)),
        personality=Personality(
            cooperation=clamp(parent.personality.cooperation + rng.uniform(-0.12, 0.12)),
            aggression=clamp(parent.personality.aggression + rng.uniform(-0.12, 0.12)),
            ambition=ambi,
        ),
        goal="survive and grow",
        settlement_id=parent.settlement_id,
        traits=traits,
        age=0,
        region_id=parent.region_id,
        subregion_id=parent.subregion_id,
    )
    parent.wealth = max(0.0, parent.wealth - BIRTH_COST)
    parent.energy = clamp(parent.energy - 0.08)
    sim.agents.append(child)
    sim.relationships.append(
        RelationshipState(
            a_id=child_id,
            b_id=parent.id,
            trust=0.25,
            affinity=0.2,
        )
    )
    if "charisma" in traits and "genius" in traits:
        detail_key = "birth_both"
    elif "charisma" in traits:
        detail_key = "birth_charisma"
    elif "genius" in traits:
        detail_key = "birth_genius"
    else:
        detail_key = "birth"
    detail = f"{child_id} born to {parent.id}"
    sim.events.append(
        EventRecord(
            turn=sim.world.turn,
            actor_id=parent.id,
            action=ActionType.birth,
            target_id=child_id,
            success=True,
            detail_key=detail_key,
            detail=detail,
        )
    )
    _remember(parent, detail)
    return child


def _emit_leadership_changes(sim: SimulationState, previous: set[str], current: set[str]) -> None:
    gained = current - previous
    lost = previous - current
    old_id = next(iter(lost)) if len(gained) == 1 and len(lost) == 1 else None
    for new_id in gained:
        sim.events.append(
            EventRecord(
                turn=sim.world.turn,
                actor_id=new_id,
                action=ActionType.lead,
                target_id=old_id,
                success=True,
                detail_key="lead_takeover" if old_id else "lead_new",
                detail=f"{new_id} became leader",
            )
        )


def apply_aging(sim: SimulationState) -> None:
    years = max(1, int(getattr(sim.world, "years_per_turn", 10)))
    for agent in sim.agents:
        if agent.alive:
            agent.age += years


def _yearly_death_chance(agent: AgentState) -> float:
    age = agent.age
    if age < 45:
        chance = 0.002
    elif age < 55:
        chance = 0.008
    elif age < 65:
        chance = 0.018
    elif age < 75:
        chance = 0.04
    else:
        chance = 0.08
    if agent.wealth < 3:
        chance += 0.01
    if agent.happiness < 0.25:
        chance += 0.008
    return min(0.18, chance)


def _death_chance(agent: AgentState, years: int = 10) -> float:
    yearly = _yearly_death_chance(agent)
    return min(0.32, 1.0 - (1.0 - yearly) ** max(1, years))


def apply_deaths(sim: SimulationState, rng: random.Random) -> None:
    years = max(1, int(getattr(sim.world, "years_per_turn", 10)))
    by_region: dict[str, list[AgentState]] = defaultdict(list)
    for agent in sim.agents:
        if agent.alive:
            by_region[_region_key(agent)].append(agent)
    for members in by_region.values():
        if len(members) <= 2:
            continue
        for agent in list(members):
            living = [a for a in members if a.alive]
            if len(living) <= 2:
                break
            if rng.random() >= _death_chance(agent, years):
                continue
            heirs = [
                a
                for a in living
                if a.id != agent.id and a.settlement_id and a.settlement_id == agent.settlement_id
            ]
            if not heirs:
                others = [a for a in living if a.id != agent.id]
                if others:
                    heirs = [min(others, key=lambda o: distance(agent.position, o.position))]
            heir = heirs[0] if heirs else None
            if heirs and agent.wealth > 0:
                share = agent.wealth / len(heirs)
                for h in heirs:
                    h.wealth += share
            agent.alive = False
            agent.energy = 0.0
            sim.relationships = [
                rel for rel in sim.relationships if rel.a_id != agent.id and rel.b_id != agent.id
            ]
            sim.events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=agent.id,
                    action=ActionType.death,
                    target_id=heir.id if heir else None,
                    success=False,
                    detail_key="death",
                    detail=f"{agent.id} died at {agent.age}",
                    deltas={"age": float(agent.age)},
                )
            )


def apply_trait_shifts(sim: SimulationState, rng: random.Random) -> None:
    for agent in sim.agents:
        if not agent.alive:
            continue
        region = agent_region(sim, agent)
        gain = TRAIT_GAIN_CHANCE * ((region.trait_rate / CHARISMA_CHANCE) if region else 1.0)
        if 16 <= agent.age <= 42:
            if "charisma" not in agent.traits and rng.random() < gain:
                agent.traits.append("charisma")
                agent.personality.ambition = max(agent.personality.ambition, 0.66)
                sim.events.append(
                    EventRecord(
                        turn=sim.world.turn,
                        actor_id=agent.id,
                        action=ActionType.trait,
                        success=True,
                        detail_key="trait_gain_charisma",
                        detail=f"{agent.id} gained charisma",
                    )
                )
            if "genius" not in agent.traits and rng.random() < gain * 0.7:
                agent.traits.append("genius")
                sim.events.append(
                    EventRecord(
                        turn=sim.world.turn,
                        actor_id=agent.id,
                        action=ActionType.trait,
                        success=True,
                        detail_key="trait_gain_genius",
                        detail=f"{agent.id} gained genius",
                    )
                )
        lose_p = TRAIT_LOSE_CHANCE + (0.05 if agent.age >= 58 else 0)
        if "charisma" in agent.traits and rng.random() < lose_p:
            agent.traits = [t for t in agent.traits if t != "charisma"]
            sim.events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=agent.id,
                    action=ActionType.trait,
                    success=False,
                    detail_key="trait_lose_charisma",
                    detail=f"{agent.id} lost charisma",
                )
            )
        if "genius" in agent.traits and rng.random() < lose_p * 0.7:
            agent.traits = [t for t in agent.traits if t != "genius"]
            sim.events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=agent.id,
                    action=ActionType.trait,
                    success=False,
                    detail_key="trait_lose_genius",
                    detail=f"{agent.id} lost genius",
                )
            )


def recompute_settlements(sim: SimulationState, rng: random.Random | None = None) -> None:
    alive = [a for a in sim.agents if a.alive]
    parent = {a.id: a.id for a in alive}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(alive):
        for b in alive[i + 1 :]:
            if _region_key(a) != _region_key(b):
                continue
            if distance(a.position, b.position) <= SETTLEMENT_DISTANCE:
                union(a.id, b.id)

    groups: dict[str, list[AgentState]] = defaultdict(list)
    for a in alive:
        groups[find(a.id)].append(a)

    settlements: list[SettlementState] = []
    idx = 0
    for members in groups.values():
        if len(members) < SETTLEMENT_MIN_SIZE:
            for m in members:
                m.settlement_id = None
            continue
        cx = sum(m.position.x for m in members) / len(members)
        cy = sum(m.position.y for m in members) / len(members)
        sid = f"s{idx + 1}"
        idx += 1
        leader = max(members, key=lambda m: leadership_score(m, rng))
        for m in members:
            m.settlement_id = sid
        settlements.append(
            SettlementState(
                id=sid,
                position=Position(x=cx, y=cy),
                member_ids=[m.id for m in members],
                shared_wealth=sum(m.wealth for m in members) * 0.05,
                leader_id=leader.id,
                region_id=members[0].region_id,
                subregion_id=members[0].subregion_id,
            )
        )
    sim.settlements = settlements


def _slice_metrics(
    sim: SimulationState,
    alive: list[AgentState],
    coop_rate: float,
    authority: float,
) -> tuple[float, float, float, float, float]:
    wealths = [a.wealth for a in alive] or [0.0]
    mean_w = sum(wealths) / len(wealths)
    var = sum((w - mean_w) ** 2 for w in wealths) / len(wealths)
    inequality = math.sqrt(var) / (mean_w + 1e-6)
    alive_ids = {a.id for a in alive}
    trusts = [r.trust for r in sim.relationships if r.a_id in alive_ids and r.b_id in alive_ids] or [0.0]
    mean_trust = sum(trusts) / len(trusts)
    mean_happiness = sum(a.happiness for a in alive) / len(alive) if alive else 0.0
    return (
        round(inequality, 4),
        round(mean_trust, 4),
        round(coop_rate, 4),
        round(authority, 4),
        round(mean_happiness, 4),
    )


def _coop_by_region(sim: SimulationState, events: list[EventRecord]) -> dict[str, tuple[int, int]]:
    ok: dict[str, int] = defaultdict(int)
    n: dict[str, int] = defaultdict(int)
    by_id = {a.id: a for a in sim.agents}
    for event in events:
        if event.action != ActionType.cooperate:
            continue
        actor = by_id.get(event.actor_id)
        rid = actor.region_id if actor and actor.region_id else "lone"
        n[rid] += 1
        if event.success:
            ok[rid] += 1
    return {rid: (ok[rid], n[rid]) for rid in n}


def compute_metrics(
    sim: SimulationState,
    cooperate_successes: int,
    action_count: int,
    micro_events: list[EventRecord] | None = None,
) -> MetricsSnapshot:
    alive = [a for a in sim.agents if a.alive]
    coop_rate = (cooperate_successes / action_count) if action_count else 0.0
    if sim.world.regions:
        authority = sum(r.institution_runtime.authority for r in sim.world.regions) / len(
            sim.world.regions
        )
    else:
        authority = sim.world.institution_runtime.authority
    inequality, mean_trust, coop_rate, authority, mean_happiness = _slice_metrics(
        sim, alive, coop_rate, authority
    )
    region_rows: list[RegionMetricsSnapshot] = []
    coop_map = _coop_by_region(sim, micro_events or [])
    if sim.world.regions:
        for region in sim.world.regions:
            rid = region.id.value
            members = agents_in_region(sim, region)
            ok, n = coop_map.get(rid, (0, 0))
            r_coop = (ok / n) if n else 0.0
            ineq, trust, coop, auth, happy = _slice_metrics(
                sim, members, r_coop, region.institution_runtime.authority
            )
            region_rows.append(
                RegionMetricsSnapshot(
                    region_id=rid,
                    subregion_id=region.subregion_id,
                    inequality=ineq,
                    mean_trust=trust,
                    cooperation_rate=coop,
                    authority=auth,
                    mean_happiness=happy,
                )
            )
    return MetricsSnapshot(
        inequality=inequality,
        mean_trust=mean_trust,
        cooperation_rate=coop_rate,
        authority=authority,
        mean_happiness=mean_happiness,
        regions=region_rows,
    )


def apply_region_readings_to_metrics(
    metrics: MetricsSnapshot,
    readings: list[RegionReading],
    world_summary: str,
) -> MetricsSnapshot:
    """Replace display metrics with semantic observer scores (LLM when wired)."""
    by_id = {r.region_id: r for r in readings}
    source = "llm" if any(r.source == "llm" for r in readings) else "heuristic"
    updated_regions: list[RegionMetricsSnapshot] = []
    for row in metrics.regions:
        reading = by_id.get(row.region_id)
        if reading is None:
            updated_regions.append(row)
            continue
        updated_regions.append(
            RegionMetricsSnapshot(
                region_id=row.region_id,
                subregion_id=row.subregion_id or reading.subregion_id,
                # Map semantic observer axes onto the existing metric slots.
                inequality=round(reading.discontent, 4),
                mean_trust=round(reading.cohesion, 4),
                cooperation_rate=round(reading.prosperity, 4),
                authority=round(clamp(1.0 - reading.tension * 0.7), 4),
                mean_happiness=round(clamp(1.0 - reading.discontent), 4),
                tension=reading.tension,
                prosperity=reading.prosperity,
                discontent=reading.discontent,
                cohesion=reading.cohesion,
                rising_archetype=reading.rising_archetype,
                trajectory=reading.trajectory,
                summary=reading.summary,
                reading_source=reading.source,
            )
        )
    if updated_regions:
        inequality = round(sum(r.inequality for r in updated_regions) / len(updated_regions), 4)
        mean_trust = round(sum(r.mean_trust for r in updated_regions) / len(updated_regions), 4)
        coop_rate = round(sum(r.cooperation_rate for r in updated_regions) / len(updated_regions), 4)
        authority = round(sum(r.authority for r in updated_regions) / len(updated_regions), 4)
        mean_happiness = round(
            sum(r.mean_happiness for r in updated_regions) / len(updated_regions), 4
        )
    else:
        inequality = metrics.inequality
        mean_trust = metrics.mean_trust
        coop_rate = metrics.cooperation_rate
        authority = metrics.authority
        mean_happiness = metrics.mean_happiness
    return MetricsSnapshot(
        inequality=inequality,
        mean_trust=mean_trust,
        cooperation_rate=coop_rate,
        authority=authority,
        mean_happiness=mean_happiness,
        regions=updated_regions or metrics.regions,
        world_summary=world_summary,
        reading_source=source,
    )


def emit_region_observation_events(
    sim: SimulationState, readings: list[RegionReading], world_summary: str
) -> list[EventRecord]:
    turn = sim.world.turn
    events: list[EventRecord] = []
    if world_summary:
        events.append(
            EventRecord(
                turn=turn,
                actor_id="world",
                action=ActionType.observe,
                detail_key="world_reading",
                detail=world_summary,
                extra={"decide": "llm" if any(r.source == "llm" for r in readings) else "heuristic", "reason": world_summary},
            )
        )
    for reading in readings:
        traj_key = f"trajectory_{reading.trajectory}"
        events.append(
            EventRecord(
                turn=turn,
                actor_id=reading.subregion_id or reading.region_id,
                action=ActionType.observe,
                detail_key=traj_key,
                detail=reading.summary,
                deltas={
                    "tension": reading.tension,
                    "prosperity": reading.prosperity,
                    "discontent": reading.discontent,
                    "cohesion": reading.cohesion,
                },
                extra={
                    "decide": reading.source,
                    "reason": reading.summary,
                    "archetype": reading.rising_archetype,
                    "trajectory": reading.trajectory,
                    "region": reading.region_id,
                },
            )
        )
    return events


def emit_region_policy_events(sim: SimulationState, policies: list[RegionPolicy]) -> list[EventRecord]:
    """Institution / polity stance for the *next* turn (visible in the event feed)."""
    turn = sim.world.turn
    events: list[EventRecord] = []
    for policy in policies:
        events.append(
            EventRecord(
                turn=turn,
                actor_id=policy.subregion_id or policy.region_id,
                action=ActionType.observe,
                detail_key=f"region_stance_{policy.action.value}",
                detail=policy.reason or f"group stance → {policy.action.value}",
                deltas={"intensity": policy.intensity},
                extra={
                    "decide": policy.source,
                    "reason": policy.reason,
                    "region": policy.region_id,
                    "group_action": policy.action.value,
                    "intensity": f"{policy.intensity:.2f}",
                    "mode": "group",
                },
            )
        )
    return events


def ensure_region_policies(sim: SimulationState) -> None:
    """First tick: seed stance with heuristics only (LLM runs once at end_of_turn)."""
    if sim.region_policies:
        return
    from simulation.llm import build_region_factsheet, heuristic_region_policy, heuristic_region_readings

    facts = build_region_factsheet(sim, None)
    readings = heuristic_region_readings(sim, facts)
    sim.region_policies = [heuristic_region_policy(f, r) for f, r in zip(facts, readings)]


def _set_id(agent: AgentState | None) -> str:
    if not agent:
        return "lone"
    return agent.subregion_id or agent.region_id or agent.settlement_id or "lone"


def _group_id(
    sim: SimulationState, agent_id: str | None, snapshot: dict[str, str] | None = None
) -> str:
    if not agent_id:
        return "lone"
    if snapshot and agent_id in snapshot:
        return snapshot[agent_id] or "lone"
    agent = next((a for a in sim.agents if a.id == agent_id), None)
    return _set_id(agent)


def summarize_group_events(
    sim: SimulationState,
    micro: list[EventRecord],
    specials: list[EventRecord],
    snapshot: dict[str, str] | None = None,
) -> list[EventRecord]:
    turn = sim.world.turn
    by_group: dict[str, dict[ActionType, int]] = defaultdict(lambda: defaultdict(int))
    cross_conflict: dict[tuple[str, str], int] = defaultdict(int)
    cross_coop: dict[tuple[str, str], int] = defaultdict(int)

    for event in micro:
        if event.action == ActionType.wait:
            continue
        src = _group_id(sim, event.actor_id, snapshot)
        dst = _group_id(sim, event.target_id, snapshot) if event.target_id else src
        if (
            event.action in {ActionType.cooperate, ActionType.conflict}
            and event.target_id
            and src != dst
            and src != "lone"
            and dst != "lone"
        ):
            pair = (src, dst) if src < dst else (dst, src)
            if event.action == ActionType.conflict:
                cross_conflict[pair] += 1
            elif event.success:
                cross_coop[pair] += 1
            continue
        by_group[src][event.action] += 1

    out: list[EventRecord] = []
    action_rank = (
        ActionType.conflict,
        ActionType.resist,
        ActionType.obey,
        ActionType.cooperate,
        ActionType.migrate,
    )
    for group, counts in by_group.items():
        action = next((a for a in action_rank if counts.get(a)), None)
        if action is None:
            continue
        n = counts[action]
        key = {
            ActionType.conflict: "group_conflict_in",
            ActionType.resist: "group_resist",
            ActionType.obey: "group_obey",
            ActionType.cooperate: "group_cooperate",
            ActionType.migrate: "group_migrate",
        }[action]
        out.append(
            EventRecord(
                turn=turn,
                actor_id=group,
                action=action,
                detail_key=key,
                detail=f"{group} {action.value} x{n}",
                deltas={"n": float(n)},
            )
        )

    for (a, b), n in cross_conflict.items():
        out.append(
            EventRecord(
                turn=turn,
                actor_id=a,
                action=ActionType.conflict,
                target_id=b,
                detail_key="group_conflict_out",
                detail=f"{a} vs {b} x{n}",
                deltas={"n": float(n)},
            )
        )
    for (a, b), n in cross_coop.items():
        out.append(
            EventRecord(
                turn=turn,
                actor_id=a,
                action=ActionType.cooperate,
                target_id=b,
                success=True,
                detail_key="group_cooperate_out",
                detail=f"{a} coop {b} x{n}",
                deltas={"n": float(n)},
            )
        )

    for event in specials:
        group = _group_id(sim, event.actor_id)
        if event.action == ActionType.birth:
            out.append(
                EventRecord(
                    turn=turn,
                    actor_id=group,
                    action=ActionType.birth,
                    target_id=event.target_id,
                    success=True,
                    detail_key="group_birth",
                    detail=event.detail,
                )
            )
        elif event.action == ActionType.death:
            out.append(
                EventRecord(
                    turn=turn,
                    actor_id=group,
                    action=ActionType.death,
                    target_id=event.actor_id,
                    detail_key="group_death",
                    detail=event.detail,
                    deltas=event.deltas,
                )
            )
        elif event.action == ActionType.lead:
            out.append(
                EventRecord(
                    turn=turn,
                    actor_id=group,
                    action=ActionType.lead,
                    target_id=event.actor_id,
                    success=True,
                    detail_key="group_lead",
                    detail=event.detail,
                )
            )
        elif event.action == ActionType.trait:
            key = event.detail_key if event.detail_key.startswith("trait_") else "trait_gain_charisma"
            out.append(
                EventRecord(
                    turn=turn,
                    actor_id=group,
                    action=ActionType.trait,
                    target_id=event.actor_id,
                    success=event.success,
                    detail_key=f"group_{key}",
                    detail=event.detail,
                )
            )

    if not out:
        out.append(
            EventRecord(
                turn=turn,
                actor_id="world",
                action=ActionType.wait,
                detail_key="group_quiet",
                detail="quiet turn",
            )
        )
    return out


def _pick_disaster(region: RegionState, rng: random.Random) -> str:
    weights: dict[str, float] = {
        "earthquake": 0.18,
        "typhoon": 0.18 if region.landform == LandformType.island else 0.08,
        "flood": 0.22 if region.climate == ClimateType.wetland else 0.1,
        "heatwave": 0.22 if region.climate == ClimateType.arid else 0.08,
        "frost": 0.22 if region.climate == ClimateType.cold else 0.06,
    }
    kinds = list(weights)
    total = sum(weights.values())
    pick = rng.random() * total
    acc = 0.0
    for kind in kinds:
        acc += weights[kind]
        if pick <= acc:
            return kind
    return kinds[-1]


def apply_welfare(sim: SimulationState) -> None:
    for region in sim.world.regions:
        rate = region.welfare_rate
        if rate <= 0:
            continue
        members = agents_in_region(sim, region)
        if len(members) < 2:
            continue
        mean = sum(a.wealth for a in members) / len(members)
        pool = 0.0
        for agent in members:
            if agent.wealth > mean:
                take = (agent.wealth - mean) * rate * 0.2
                agent.wealth -= take
                pool += take
        needy = [a for a in members if a.wealth < mean]
        if not needy or pool <= 0:
            continue
        share = pool / len(needy)
        for agent in needy:
            agent.wealth += share
            agent.happiness = clamp(agent.happiness + 0.015 * rate)
        region.institution_runtime.authority = clamp(region.institution_runtime.authority + 0.01 * rate)


def apply_disasters(sim: SimulationState, rng: random.Random, skip_quake: set[str] | None = None) -> list[EventRecord]:
    events: list[EventRecord] = []
    skip_quake = skip_quake or set()
    targets = sim.world.regions or []
    if not targets:
        fake = RegionState(
            id=sim.world.geography if sim.world.geography != GeographyType.world else GeographyType.asia,
            landform=sim.world.landform,
            climate=sim.world.climate,
            disaster_frequency=sim.world.disaster_frequency,
            resource_pool=sim.world.resource_pool,
        )
        targets = [fake]
    for region in targets:
        freq = region.disaster_frequency
        if freq <= 0 or rng.random() >= freq * 0.28:
            continue
        kind = _pick_disaster(region, rng)
        sid = region.subregion_id or region.id.value
        if kind == "earthquake" and sid in skip_quake:
            continue
        hit = agents_in_region(sim, region)
        if not sim.world.regions:
            hit = [a for a in sim.agents if a.alive]
        if not hit:
            continue
        if kind in ("typhoon", "earthquake") and len(hit) > 2:
            hit = rng.sample(hit, max(2, len(hit) // 2))
        loss = 0.0
        for agent in hit:
            if kind == "heatwave":
                agent.energy = clamp(agent.energy - 0.12)
                agent.happiness = clamp(agent.happiness - 0.04)
            elif kind == "frost":
                agent.energy = clamp(agent.energy - 0.1)
                agent.wealth = max(0.0, agent.wealth - 1.2)
                loss += 1.2
            elif kind == "flood":
                agent.wealth = max(0.0, agent.wealth - 1.6)
                agent.happiness = clamp(agent.happiness - 0.05)
                loss += 1.6
            elif kind == "typhoon":
                agent.energy = clamp(agent.energy - 0.08)
                agent.wealth = max(0.0, agent.wealth - 1.4)
                loss += 1.4
            else:
                agent.wealth = max(0.0, agent.wealth - 2.0)
                agent.happiness = clamp(agent.happiness - 0.06)
                loss += 2.0
        food_hit = 4.0 + 10.0 * freq
        if kind in ("flood", "frost", "heatwave"):
            region.resource_pool = max(0.0, region.resource_pool - food_hit)
        lon, lat = SUBREGION_CENTERS.get(sid, (0.0, 0.0))
        alert = "red" if kind in ("earthquake", "typhoon") else "yellow"
        events.append(
            EventRecord(
                turn=sim.world.turn,
                actor_id=sid,
                action=ActionType.disaster,
                detail_key=f"disaster_{kind}",
                detail=f"{kind} hit {len(hit)} agents in {sid}",
                deltas={"n": float(len(hit)), "loss": loss},
                lon=lon,
                lat=lat,
                alert=alert,
            )
        )
    return events


def apply_regime_drift(sim: SimulationState, rng: random.Random) -> list[EventRecord]:
    events: list[EventRecord] = []
    for region in sim.world.regions:
        inst = region.institution
        auth = region.institution_runtime.authority
        members = agents_in_region(sim, region)
        ineq = region.initial_values.inequality
        if len(members) >= 3:
            mean = sum(a.wealth for a in members) / len(members)
            var = sum((a.wealth - mean) ** 2 for a in members) / len(members)
            ineq = min(1.0, (var ** 0.5) / max(mean, 1.0))
        resist = 0.0
        if members:
            resist = sum(1 for a in members if a.allegiance == Allegiance.resist or a.personality.ambition > 0.7) / len(
                members
            )
        nxt = inst
        if inst == InstitutionType.democracy:
            if auth > 0.62 and ineq > 0.55 and rng.random() < 0.07:
                nxt = InstitutionType.autocracy
            elif resist > 0.42 and auth < 0.38 and rng.random() < 0.05:
                nxt = InstitutionType.anarchy
        elif inst == InstitutionType.autocracy:
            if resist > 0.38 and auth < 0.48 and rng.random() < 0.08:
                nxt = InstitutionType.democracy if ineq < 0.55 else InstitutionType.anarchy
        else:
            if auth > 0.45 and rng.random() < 0.09:
                nxt = InstitutionType.democracy if resist < 0.35 else InstitutionType.autocracy
        if nxt == inst:
            continue
        prev = inst
        region.institution = nxt
        sid = region.subregion_id or region.id.value
        lon, lat = SUBREGION_CENTERS.get(sid, (0.0, 0.0))
        events.append(
            EventRecord(
                turn=sim.world.turn,
                actor_id=sid,
                action=ActionType.regime,
                detail_key="regime_shift",
                detail=f"{sid} {prev.value} -> {nxt.value}",
                lon=lon,
                lat=lat,
                alert="yellow",
                extra={"from": prev.value, "to": nxt.value},
            )
        )
    if sim.world.regions:
        sim.world.institution = sim.world.regions[0].institution
    return events


def end_of_turn(
    sim: SimulationState,
    cooperate_successes: int,
    action_count: int,
    rng: random.Random,
    micro_events: list[EventRecord] | None = None,
) -> None:
    previous_leaders = {s.leader_id for s in sim.settlements if s.leader_id}
    snapshot = {a.id: _set_id(a) for a in sim.agents}
    marker = len(sim.events)
    apply_births(sim, rng)
    apply_aging(sim)
    apply_deaths(sim, rng)
    apply_trait_shifts(sim, rng)
    recompute_settlements(sim, rng)
    current_leaders = {s.leader_id for s in sim.settlements if s.leader_id}
    _emit_leadership_changes(sim, previous_leaders, current_leaders)
    specials = sim.events[marker:]
    llm_decisions = [
        event
        for event in (micro_events or [])
        if event.extra.get("decide") == "llm" and event.action != ActionType.wait
    ]
    grouped = summarize_group_events(sim, micro_events or [], specials, snapshot)
    historic = apply_historic_quakes(sim)
    epidemics = apply_epidemics(sim, rng)
    weather = apply_weather_shocks(sim, rng)
    skip_quake = {e.actor_id for e in historic}
    disasters = apply_disasters(sim, rng, skip_quake)
    regimes = apply_regime_drift(sim, rng)
    if sim.world.regions:
        for region in sim.world.regions:
            regen = 2.0 + 3.0 * region.education_level
            regen *= 0.65 + 0.7 * getattr(region, "trade_openness", 0.5)
            if region.climate == ClimateType.arid:
                regen *= 0.45
            elif region.climate == ClimateType.wetland:
                regen *= 1.15
            elif region.climate == ClimateType.cold:
                regen *= 0.7
                for agent in agents_in_region(sim, region):
                    agent.energy = clamp(agent.energy - 0.03)
            region.resource_pool += regen
            region.institution_runtime.authority = clamp(region.institution_runtime.authority)
        sim.world.resource_pool = sum(r.resource_pool for r in sim.world.regions)
        sim.world.institution_runtime.authority = clamp(
            sum(r.institution_runtime.authority for r in sim.world.regions) / len(sim.world.regions)
        )
    else:
        regen = 2.0 + 3.0 * sim.world.education_level
        if sim.world.climate == ClimateType.arid:
            regen *= 0.45
        elif sim.world.climate == ClimateType.wetland:
            regen *= 1.15
        elif sim.world.climate == ClimateType.cold:
            regen *= 0.7
            for agent in sim.agents:
                if agent.alive:
                    agent.energy = clamp(agent.energy - 0.03)
        sim.world.resource_pool += regen
        sim.world.institution_runtime.authority = clamp(sim.world.institution_runtime.authority)
    apply_welfare(sim)
    metrics = compute_metrics(sim, cooperate_successes, action_count, micro_events or [])
    observe_input = (micro_events or []) + historic + epidemics + weather + disasters + regimes + specials
    # One LLM pass per region: semantic reading + next-turn group/institution stance.
    readings, policies, world_summary = observe_and_steer_regions(sim, observe_input)
    metrics = apply_region_readings_to_metrics(metrics, readings, world_summary)
    sim.region_readings = readings
    sim.region_policies = policies
    sim.world_summary = world_summary
    sim.last_metrics = metrics
    observe_events = emit_region_observation_events(sim, readings, world_summary)
    policy_events = emit_region_policy_events(sim, policies)
    # Keep group LLM enactments + semantic region readings / next stance visible.
    sim.events = (
        sim.events[:marker]
        + llm_decisions
        + observe_events
        + policy_events
        + grouped
        + historic
        + epidemics
        + weather
        + disasters
        + regimes
    )
    turn = sim.world.turn
    alive = sum(1 for a in sim.agents if a.alive)
    turn_events = [e for e in sim.events if e.turn == turn]
    conflicts = sum(1 for e in turn_events if e.action == ActionType.conflict)
    coops = sum(1 for e in turn_events if e.action == ActionType.cooperate)
    births = sum(1 for e in turn_events if e.action == ActionType.birth)
    deaths = sum(1 for e in turn_events if e.action == ActionType.death)
    sim.history.append(
        HistoryRecord(
            turn=turn,
            summary=(
                f"turn={turn} pop={alive} "
                f"clash={conflicts} coop={coops} birth={births} death={deaths}"
                + (f" | {world_summary}" if world_summary else "")
            ),
            metrics=metrics,
        )
    )
    sim.status = "running"
    sim.world.turn += 1


def _turns_until_year_cap(sim: SimulationState) -> int:
    years = max(1, int(getattr(sim.world, "years_per_turn", YEARS_PER_TURN)))
    max_turn = (MAX_CALENDAR_YEAR - int(sim.world.start_year)) // years
    return max(0, max_turn - int(sim.world.turn))


def tick(sim: SimulationState, n: int = 1) -> SimulationState:
    remaining = _turns_until_year_cap(sim)
    steps = min(max(0, n), remaining)
    if steps <= 0:
        return sim
    rng = random.Random(sim.world.seed + sim.world.turn * 1009)
    for _ in range(steps):
        ensure_region_policies(sim)
        choices = decide_actions(sim, rng)
        coop_ok, action_count, micro_events = resolve_actions(sim, choices, rng)
        end_of_turn(sim, coop_ok, action_count, rng, micro_events)
        rng = random.Random(sim.world.seed + sim.world.turn * 1009)
    return sim


create_simulation = create_simulation
