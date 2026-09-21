"""Same-ID cross-world frame for analysis summaries.

Only a1–a{roster_size} are the shared identity. Descendant IDs are assigned
per simulation and must not be treated as the same person across variants.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from simulation.experiment import CONTINENT_IDS, EXPERIMENT_POPULATION_PER_REGION

    INITIAL_ROSTER_SIZE = EXPERIMENT_POPULATION_PER_REGION * len(CONTINENT_IDS)
except Exception:  # pragma: no cover - analysis may run without backend on path
    INITIAL_ROSTER_SIZE = 5000

DIED_LINE = re.compile(r"^\s+(a\d+) died\b")
SPOT_ID = re.compile(r"^スポットライト ID:\s*(a\d+|—|-)?")
SPOT_ROLE = re.compile(r"^スポットライト役割:\s*(\S+)")
LEADER_LINE = re.compile(
    r"^s\S+\s+\|\s+(\S+)\s+\|\s+人数\s+\d+\s+\|\s+指導者\s+.*?(a\d+)"
)
AGENT_ID = re.compile(r"^a(\d+)$")

MAX_SURVIVOR_ROWS = 24


def agent_index(agent_id: str) -> int | None:
    m = AGENT_ID.fullmatch(agent_id)
    return int(m.group(1)) if m else None


def is_initial(agent_id: str, roster_size: int = INITIAL_ROSTER_SIZE) -> bool:
    n = agent_index(agent_id)
    return n is not None and 1 <= n <= roster_size


@dataclass
class VariantView:
    alive_initial: set[str]
    leaders: dict[str, str]  # agent_id -> region_id
    spotlight_id: str | None
    spotlight_role: str | None


@dataclass
class SameIdStats:
    order: tuple[str, ...]
    headers: list[str]
    roster_size: int
    views: dict[str, VariantView]
    pattern_counts: dict[tuple[bool, ...], int]
    survivors: list[str]
    roster_meta: dict[str, dict[str, str]] = field(default_factory=dict)


def parse_report_txt(text: str, *, roster_size: int = INITIAL_ROSTER_SIZE) -> VariantView:
    died: set[str] = set()
    leaders: dict[str, str] = {}
    spotlight_id: str | None = None
    spotlight_role: str | None = None
    for line in text.splitlines():
        m = DIED_LINE.match(line)
        if m:
            died.add(m.group(1))
            continue
        m = SPOT_ID.match(line)
        if m:
            raw = (m.group(1) or "").strip()
            spotlight_id = raw if raw.startswith("a") else None
            continue
        m = SPOT_ROLE.match(line)
        if m and m.group(1) not in {"—", "-"}:
            spotlight_role = m.group(1)
            continue
        m = LEADER_LINE.match(line)
        if m:
            leaders[m.group(2)] = m.group(1)
    alive = {f"a{i}" for i in range(1, roster_size + 1) if f"a{i}" not in died}
    return VariantView(
        alive_initial=alive,
        leaders=leaders,
        spotlight_id=spotlight_id,
        spotlight_role=spotlight_role,
    )


def view_from_json_snapshot(payload: dict[str, Any], *, roster_size: int) -> VariantView | None:
    snap = payload.get("same_id")
    if not isinstance(snap, dict) or "initial_alive_ids" not in snap:
        return None
    alive = {str(x) for x in snap.get("initial_alive_ids") or [] if is_initial(str(x), roster_size)}
    leaders: dict[str, str] = {}
    for row in snap.get("leaders") or []:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("id") or "")
        if aid:
            leaders[aid] = str(row.get("region_id") or "—")
    summary = payload.get("experiment_summary") or {}
    return VariantView(
        alive_initial=alive,
        leaders=leaders,
        spotlight_id=snap.get("spotlight_agent_id") or summary.get("spotlight_agent_id"),
        spotlight_role=snap.get("spotlight_role") or summary.get("spotlight_role"),
    )


def resolve_report_txt(repo_root: Path, payload: dict[str, Any]) -> Path | None:
    rel = payload.get("report_txt")
    if rel:
        path = repo_root / rel
        if path.exists():
            return path
    return None


def load_variant_view(
    repo_root: Path,
    payload: dict[str, Any],
    *,
    roster_size: int = INITIAL_ROSTER_SIZE,
) -> VariantView:
    from_json = view_from_json_snapshot(payload, roster_size=roster_size)
    if from_json is not None:
        return from_json
    path = resolve_report_txt(repo_root, payload)
    if path is None:
        raise FileNotFoundError("same-id: missing same_id snapshot and report_txt")
    return parse_report_txt(path.read_text(encoding="utf-8"), roster_size=roster_size)


def load_roster_meta(seed: int | None) -> dict[str, dict[str, str]]:
    if seed is None:
        return {}
    try:
        from simulation.experiment import get_experiment_roster
    except Exception:
        return {}
    out: dict[str, dict[str, str]] = {}
    for agent in get_experiment_roster(int(seed)):
        traits = ",".join(agent.traits) if agent.traits else "—"
        out[agent.id] = {
            "region": agent.region_id or "—",
            "traits": traits,
        }
    return out


def stats_from_payloads(
    repo_root: Path,
    payloads: dict[str, dict[str, Any]],
    *,
    order: tuple[str, ...],
    headers: list[str],
    roster_size: int = INITIAL_ROSTER_SIZE,
) -> SameIdStats:
    views = {vid: load_variant_view(repo_root, payloads[vid], roster_size=roster_size) for vid in order}
    seed = payloads[order[0]].get("experiment_seed")
    return collect_same_id_stats(
        order=order,
        headers=headers,
        views=views,
        roster_size=roster_size,
        seed=seed if seed is not None else None,
    )


def collect_same_id_stats(
    *,
    order: tuple[str, ...],
    headers: list[str],
    views: dict[str, VariantView],
    roster_size: int = INITIAL_ROSTER_SIZE,
    seed: int | None = None,
) -> SameIdStats:
    patterns: dict[tuple[bool, ...], int] = Counter()
    survivors: list[str] = []
    for i in range(1, roster_size + 1):
        aid = f"a{i}"
        mask = tuple(aid in views[vid].alive_initial for vid in order)
        patterns[mask] += 1
        if any(mask):
            survivors.append(aid)
    return SameIdStats(
        order=order,
        headers=headers,
        roster_size=roster_size,
        views=views,
        pattern_counts=dict(patterns),
        survivors=survivors,
        roster_meta=load_roster_meta(seed),
    )


def _mark(alive: bool) -> str:
    return "生存" if alive else "死亡"


def _leader_cell(stats: SameIdStats, agent_id: str, vid: str) -> str:
    region = stats.views[vid].leaders.get(agent_id)
    if not region:
        return "—"
    return f"指導者@{region}"


def _count_n_alive(stats: SameIdStats, n: int) -> int:
    return sum(c for mask, c in stats.pattern_counts.items() if sum(mask) == n)


def _one_world_breakdown(stats: SameIdStats) -> dict[str, int]:
    out = {vid: 0 for vid in stats.order}
    for mask, count in stats.pattern_counts.items():
        if sum(mask) != 1:
            continue
        out[stats.order[mask.index(True)]] += count
    return out


def _survivor_sort_key(stats: SameIdStats, agent_id: str) -> tuple[int, int, int]:
    n_alive = sum(agent_id in stats.views[vid].alive_initial for vid in stats.order)
    n_lead = sum(agent_id in stats.views[vid].leaders for vid in stats.order)
    return (-n_lead, -n_alive, agent_index(agent_id) or 0)


def _pick_survivor_rows(stats: SameIdStats) -> list[str]:
    ranked = sorted(stats.survivors, key=lambda aid: _survivor_sort_key(stats, aid))
    if len(ranked) <= MAX_SURVIVOR_ROWS:
        return ranked
    leaders_first = [aid for aid in ranked if any(aid in stats.views[vid].leaders for vid in stats.order)]
    rest = [aid for aid in ranked if aid not in leaders_first]
    picked = leaders_first + rest
    return picked[:MAX_SURVIVOR_ROWS]


def _alive_cell(stats: SameIdStats, agent_id: str, vid: str) -> str:
    alive = agent_id in stats.views[vid].alive_initial
    lead = _leader_cell(stats, agent_id, vid)
    if lead != "—":
        return lead
    return _mark(alive)


def render_same_id_markdown(stats: SameIdStats, *, heading: str = "## 1c. 同一 ID 比較") -> str:
    n0 = stats.pattern_counts.get(tuple(False for _ in stats.order), 0)
    n1 = _count_n_alive(stats, 1)
    n2plus = sum(_count_n_alive(stats, n) for n in range(2, len(stats.order) + 1))
    n_all = stats.pattern_counts.get(tuple(True for _ in stats.order), 0)
    one_world = _one_world_breakdown(stats)
    one_cells = " / ".join(str(one_world[vid]) for vid in stats.order)

    header = "| パターン | 人数 |"
    sep = "|----------|------|"
    lines = [
        heading,
        "",
        "比較してよいのは初期名簿 **a1–a"
        f"{stats.roster_size}** だけ。子孫の ID はシミュレーションごとに採番されるので、世界をまたいで同一人物ではない。",
        "",
        header,
        sep,
        f"| 4 世界すべてで死亡 | {n0} |",
        f"| **1 世界だけ生存** | **{n1}**（{one_cells}） |",
        f"| 2 世界以上で生存 | {n2plus} |",
        f"| 4 世界すべてで生存 | {n_all} |",
        "",
    ]

    rows = _pick_survivor_rows(stats)
    if rows:
        col_h = "| ID | 出身 | traits | " + " | ".join(stats.headers) + " |"
        col_s = "|----|------|--------|" + "|".join(["------"] * len(stats.headers)) + "|"
        lines.extend(
            [
                "### 初期名簿の期末生存者",
                "",
            ]
        )
        if len(stats.survivors) > len(rows):
            lines.append(
                f"生存 {len(stats.survivors)} 人のうち、指導者を優先して {len(rows)} 人を表示。"
            )
            lines.append("")
        lines.extend([col_h, col_s])
        for aid in rows:
            meta = stats.roster_meta.get(aid, {})
            cells = [_alive_cell(stats, aid, vid) for vid in stats.order]
            lines.append(
                "| "
                + " | ".join(
                    [aid, meta.get("region", "—"), meta.get("traits", "—"), *cells]
                )
                + " |"
            )
        lines.append("")
    else:
        lines.extend(["初期名簿の期末生存者はいない。", ""])

    spot_h = "| | " + " | ".join(stats.headers) + " |"
    spot_s = "|--|" + "|".join(["------"] * len(stats.headers)) + "|"
    ids: list[str] = []
    roles: list[str] = []
    origins: list[str] = []
    for vid in stats.order:
        view = stats.views[vid]
        sid = view.spotlight_id or "—"
        ids.append(sid)
        roles.append(view.spotlight_role or "—")
        if sid.startswith("a") and is_initial(sid, stats.roster_size):
            origins.append("初期名簿")
        elif sid.startswith("a"):
            origins.append("子孫（他世界と別人）")
        else:
            origins.append("—")
    lines.extend(
        [
            "### スポットライト（世界ごとに別選択）",
            "",
            spot_h,
            spot_s,
            "| ID | " + " | ".join(ids) + " |",
            "| 役割 | " + " | ".join(roles) + " |",
            "| 出自 | " + " | ".join(origins) + " |",
            "",
            "読み方: 200 年後の初期名簿はほとんど死亡する。同一 ID の差は「どの社会で一人生き残ったか／指導者になったか」に出る。"
            " 期末人口の大半は子孫。`spotlight_role` は人物の職業ではなく、所属地域の台頭タイプを貼った値。",
            "",
        ]
    )
    return "\n".join(lines)


def render_same_id_summary_frame(stats: SameIdStats) -> str:
    return render_same_id_markdown(stats, heading="## 同一 ID 比較")


def same_id_document(stats: SameIdStats, *, run_id: str, analysis_date: str) -> str:
    body = render_same_id_markdown(stats, heading="## 集計")
    return (
        f"# 同一 ID 比較 — {run_id}\n\n"
        f"自動生成: {analysis_date}（初期名簿 a1–a{stats.roster_size} のみ）\n\n"
        f"{body}"
    )


def snapshot_from_sim(sim: Any, *, roster_size: int = INITIAL_ROSTER_SIZE) -> dict[str, Any]:
    """Compact end-state for future JSON dumps (avoids grouped event logs)."""
    leaders = []
    for settlement in getattr(sim, "settlements", []) or []:
        lid = getattr(settlement, "leader_id", None)
        if not lid:
            continue
        leaders.append(
            {
                "id": lid,
                "region_id": getattr(settlement, "region_id", None),
                "settlement_id": getattr(settlement, "id", None),
                "initial_roster": is_initial(lid, roster_size),
            }
        )
    initial_alive = [
        agent.id
        for agent in getattr(sim, "agents", [])
        if getattr(agent, "alive", False) and is_initial(agent.id, roster_size)
    ]
    return {
        "initial_roster_size": roster_size,
        "initial_alive_ids": initial_alive,
        "leaders": leaders,
    }


def cross_run_same_id_row(run_id: str, stats: SameIdStats) -> str:
    n0 = stats.pattern_counts.get(tuple(False for _ in stats.order), 0)
    n1 = _count_n_alive(stats, 1)
    n2plus = sum(_count_n_alive(stats, n) for n in range(2, len(stats.order) + 1))
    init_leaders = sorted(
        {
            aid
            for view in stats.views.values()
            for aid in view.leaders
            if is_initial(aid, stats.roster_size)
        },
        key=lambda x: agent_index(x) or 0,
    )
    lead = ", ".join(init_leaders) if init_leaders else "—"
    return f"| {run_id} | {n0} | {n1} | {n2plus} | {lead} |"
