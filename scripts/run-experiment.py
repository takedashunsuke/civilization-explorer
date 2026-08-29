#!/usr/bin/env python3
"""Run controlled experiment without browser (4 worlds × N turns).

Uses the simulation engine directly — Backend server is NOT required.
Output: result/raw/civ-{variant}-AD{year}-turn{N}.txt

Usage (from repo root):
  ./scripts/run-experiment.sh
  # or
  cd backend && source .venv/bin/activate && python ../scripts/run-experiment.py
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from simulation import create_simulation, tick  # noqa: E402
from simulation.experiment import (  # noqa: E402
    EXPERIMENT_SEED,
    WORLD_VARIANT_IDS,
    _VARIANT_LABEL_JA,
    experiment_summary,
    fresh_roster_copy,
    world_params_for_variant,
)
from config import get_settings  # noqa: E402
from simulation.llm import describe_provider  # noqa: E402
from simulation.models import SimulationState  # noqa: E402

DEFAULT_TURNS = 10
DEFAULT_START_YEAR = 1000
DEFAULT_YEARS_PER_TURN = 10


def _line(title: str, body: object | None = None) -> str:
    if body is None or body == "":
        return f"{title}: —"
    return f"{title}: {body}"


def _section(title: str) -> str:
    return f"\n{'=' * 72}\n{title}\n{'=' * 72}\n"


def _subsection(title: str) -> str:
    return f"\n--- {title} ---\n"


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(value * 100)}%"


def _calendar_year(sim: SimulationState, turn: int | None = None) -> int:
    t = sim.world.turn if turn is None else turn
    return sim.world.start_year + t * sim.world.years_per_turn


def _export_filename(variant: str, milestone_year: int, turn: int) -> str:
    return f"civ-{variant}-AD{milestone_year}-turn{turn}.txt"


def build_report(sim: SimulationState, summary: dict) -> str:
    lines: list[str] = []
    turn = sim.world.turn
    ypt = sim.world.years_per_turn
    milestone_year = _calendar_year(sim)
    alive = [a for a in sim.agents if a.alive]
    events = sorted(sim.events, key=lambda e: (e.turn, e.actor_id))
    action_counts = Counter(e.action.value for e in events)

    lines.append("Civilization Explorer — マイルストーン・レポート")
    lines.append(f"生成: {datetime.now(timezone.utc).isoformat()}")
    lines.append(_line("シミュレーション ID", sim.id))
    lines.append(_line("シード", sim.world.seed))
    lines.append(_line("対照実験", "yes"))
    lines.append(_line("環境パターン", _VARIANT_LABEL_JA.get(sim.experiment_variant or "", sim.experiment_variant)))
    lines.append(_line("実験シード", sim.experiment_seed))

    lines.append(_section("節目"))
    lines.append(_line("暦年", f"AD {milestone_year}"))
    lines.append(_line("ターン", f"{turn}（1ターン={ypt}年）"))
    lines.append(_line("節目の年", milestone_year))

    initial_pop = sim.world.initial_population or len(sim.agents)
    lines.append(_section("累計指標"))
    lines.append(_line("生存人口", f"{len(alive)}（{len(alive) - initial_pop:+d}）"))
    lines.append(_line("集落数", len(sim.settlements)))
    lines.append(_line("争い（累計）", summary.get("conflicts_total")))
    lines.append(_line("共同（累計）", summary.get("cooperations_total")))

    lines.append(_section("実験サマリー（API）"))
    for key, label in [
        ("population_alive", "生存人口"),
        ("population_delta_pct", "人口変化%"),
        ("resource_pool", "共有資源（合計）"),
        ("trade_openness_mean", "交易開放（平均）"),
        ("conflicts_total", "争い"),
        ("cooperations_total", "共同"),
        ("regime_shifts", "体制転換"),
        ("disasters", "災害"),
        ("dominant_archetype", "台頭タイプ"),
    ]:
        lines.append(_line(label, summary.get(key)))
    if summary.get("spotlight_agent_id"):
        lines.append(_line("スポットライト ID", summary["spotlight_agent_id"]))
        lines.append(_line("スポットライト役割", summary.get("spotlight_role")))

    if sim.region_readings:
        lines.append(_section("地域観測（最新ターン）"))
        for r in sim.region_readings:
            lines.append(_subsection(r.region_id))
            lines.append(_line("緊張", _pct(r.tension)))
            lines.append(_line("繁栄", _pct(r.prosperity)))
            lines.append(_line("不満", _pct(r.discontent)))
            lines.append(_line("結束", _pct(r.cohesion)))
            lines.append(_line("台頭タイプ", r.rising_archetype))
            lines.append(_line("軌道", r.trajectory))
            lines.append(_line("ソース", r.source or "—"))
            if r.summary:
                lines.append(r.summary)

    if sim.world.regions:
        lines.append(_section("列ごとの環境・社会（スナップショット）"))
        for r in sim.world.regions:
            lines.append(_subsection(r.id))
            lines.append(_line("サブ地域", r.subregion_id))
            lines.append(_line("制度", r.institution.value))
            lines.append(_line("税率", _pct(r.tax_rate)))
            lines.append(_line("交易開放", _pct(r.trade_openness)))
            lines.append(_line("共有資源", f"{r.resource_pool:.1f}"))
            lines.append(_line("災害頻度", _pct(r.disaster_frequency)))

    if sim.settlements:
        lines.append(_section("集落・指導者"))
        for s in sorted(sim.settlements, key=lambda x: -len(x.member_ids)):
            leader_name = "—"
            if s.leader_id:
                leader = next((a for a in sim.agents if a.id == s.leader_id), None)
                if leader:
                    leader_name = f"{leader.name} ({leader.id})"
            lines.append(f"{s.id} | {s.region_id} | 人数 {len(s.member_ids)} | 指導者 {leader_name}")

    lines.append(_section("出来事サマリー（種別ごとの件数）"))
    for action, count in action_counts.most_common():
        lines.append(f"{action}: {count}")

    lines.append(_section("出来事ログ（全件・ターン順）"))
    current_turn = -1
    for e in events:
        if e.turn != current_turn:
            current_turn = e.turn
            year = _calendar_year(sim, e.turn)
            lines.append(_subsection(f"ターン {e.turn}（AD {year}）"))
        target = f" → {e.target_id}" if e.target_id else ""
        success = ""
        if e.success is True:
            success = " [成功]"
        elif e.success is False:
            success = " [失敗]"
        lines.append(f"  {e.action.value} {e.actor_id}{target}{success}")
        if e.detail:
            lines.append(f"    {e.detail}")

    lines.append("\n--- end of report ---\n")
    return "\n".join(lines)


def update_manifest(out_dir: Path, records: list[dict]) -> None:
    manifest_path = ROOT / "result" / "manifest.json"
    if not manifest_path.exists():
        return
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_variant = {r["variant"]: r for r in records}
    for entry in data.get("files", []):
        vid = entry.get("variant")
        if vid in by_variant:
            rec = by_variant[vid]
            entry["path"] = f"result/raw/{rec['filename']}"
            entry["json_path"] = f"result/raw/{rec['json_filename']}"
            entry["status"] = "done"
    data["recorded_at"] = datetime.now(timezone.utc).isoformat()
    data["milestone_turn"] = records[0]["turn"] if records else data.get("milestone_turn")
    settings = get_settings()
    data["llm_provider"] = settings.llm_provider
    if settings.llm_provider == "ollama":
        data["ollama_model"] = settings.ollama_model
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run controlled experiment without browser")
    parser.add_argument(
        "--variant",
        choices=list(WORLD_VARIANT_IDS),
        help="Run a single variant (default: all four)",
    )
    parser.add_argument("--turns", type=int, default=DEFAULT_TURNS, help="Ticks to advance (default: 10 = 100 years)")
    parser.add_argument("--seed", type=int, default=EXPERIMENT_SEED)
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "result" / "raw",
        help="Output directory for .txt reports",
    )
    args = parser.parse_args()

    variants = [args.variant] if args.variant else list(WORLD_VARIANT_IDS)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    llm = describe_provider()
    print(
        f"Controlled experiment — seed={args.seed}, turns={args.turns} "
        f"({args.turns * DEFAULT_YEARS_PER_TURN} years), LLM={llm.get('provider')} "
        f"(wired={llm.get('wired')})",
    )
    if llm.get("provider") == "ollama":
        print(f"  Ollama: {llm.get('ollama_model')} @ {get_settings().ollama_base_url}")
    records: list[dict] = []

    for variant in variants:
        print(f"  → {variant} ({_VARIANT_LABEL_JA.get(variant, variant)}) ...", flush=True)
        params = world_params_for_variant(variant, args.seed, args.start_year)
        roster = fresh_roster_copy(args.seed)
        sim_id = str(uuid.uuid4())
        sim = create_simulation(sim_id, params, agent_roster=roster)
        sim.controlled_experiment = True
        sim.experiment_variant = variant
        sim.experiment_seed = args.seed
        sim.status = "running"
        tick(sim, n=args.turns)
        summary = experiment_summary(sim)
        report = build_report(sim, summary)
        filename = _export_filename(variant, _calendar_year(sim), sim.world.turn)
        out_path = args.out_dir / filename
        out_path.write_text(report, encoding="utf-8")
        json_name = filename.replace(".txt", ".json")
        json_payload = {
            "format": "civ-experiment-result-v1",
            "variant": variant,
            "variant_label_ja": _VARIANT_LABEL_JA.get(variant, variant),
            "experiment_seed": args.seed,
            "simulation_id": sim_id,
            "turn": sim.world.turn,
            "calendar_year": _calendar_year(sim),
            "llm": llm,
            "experiment_summary": summary,
            "report_txt": f"result/raw/{filename}",
        }
        json_path = args.out_dir / json_name
        json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"     saved {out_path.name}, {json_path.name} | pop={summary['population_alive']} "
            f"conflicts={summary['conflicts_total']} archetype={summary['dominant_archetype']}",
        )
        records.append({
            "variant": variant,
            "filename": filename,
            "json_filename": json_name,
            "turn": sim.world.turn,
            "summary": summary,
        })

    update_manifest(args.out_dir, records)
    print(f"\nDone. {len(records)} report(s) in {args.out_dir}")
    print("Next: analysis/prompt.md で LLM 比較 → analysis/summary.md に転記")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
