#!/usr/bin/env python3
"""Run controlled experiment without browser (4 worlds × N turns).

Uses the simulation engine directly — Backend server is NOT required.
Output: result/raw/run-NNN/civ-{variant}-AD{year}-turn{N}.{txt,json}

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
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(SCRIPTS))

from experiment_runs import (  # noqa: E402
    analysis_run_dir,
    relative_repo_path,
    resolve_run_dir,
    upsert_run_manifest,
    validate_series,
)

from simulation import create_simulation, tick  # noqa: E402
from simulation.experiment import (  # noqa: E402
    ALL_VARIANT_IDS,
    EXPERIMENT_SEED,
    PROTOCOL_ENVIRONMENT,
    PROTOCOL_RESILIENCE,
    experiment_summary,
    fresh_roster_copy,
    prepare_experiment_sim,
    protocol_for_variant,
    variant_ids_for_protocol,
    variant_label_ja,
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


def build_report(sim: SimulationState, summary: dict, *, run_id: str | None = None) -> str:
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
    lines.append(_line("環境パターン", variant_label_ja(sim.experiment_variant or "")))
    lines.append(_line("プロトコル", sim.experiment_protocol or "—"))
    if sim.shock_pulse_turns:
        lines.append(_line("強制ショック turn", ",".join(str(t) for t in sim.shock_pulse_turns)))
    lines.append(_line("実験シード", sim.experiment_seed))
    if run_id:
        lines.append(_line("実行回", run_id))

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
        ("pop_trough", "人口最下点"),
        ("pop_recovery_ratio", "人口回復率"),
        ("pop_retention_ratio", "人口保持率"),
        ("disaster_deaths", "災害死"),
        ("regime_break", "制度破綻"),
        ("coop_vs_conflict_post_shock", "ショック後協力比"),
        ("resilience_label", "レジリエンスラベル"),
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


def update_manifest(
    run_dir: Path,
    run_id: str,
    records: list[dict],
    *,
    experiment_seed: int,
    start_year: int,
    years_per_turn: int,
    milestone_turn: int,
    protocol: str,
) -> None:
    settings = get_settings()
    observe = settings.ollama_model if settings.llm_provider == "ollama" else None
    decide = (settings.ollama_model_decision or "").strip() if observe else ""
    ollama_label = observe
    if observe and decide and decide != observe:
        ollama_label = f"{observe}+decide:{decide}"
    upsert_run_manifest(
        ROOT / "result" / "manifest.json",
        run_id=run_id,
        run_dir=run_dir,
        repo_root=ROOT,
        records=records,
        llm_provider=settings.llm_provider,
        ollama_model=ollama_label,
        milestone_turn=milestone_turn,
        milestone_years=milestone_turn * years_per_turn,
        start_year=start_year,
        years_per_turn=years_per_turn,
        experiment_seed=experiment_seed,
        protocol=protocol,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run controlled experiment without browser")
    parser.add_argument(
        "--protocol",
        choices=[PROTOCOL_ENVIRONMENT, PROTOCOL_RESILIENCE],
        default=PROTOCOL_ENVIRONMENT,
        help="environment=資源・災害ノブ / resilience=同一ショック×社会構造 (Phase C)",
    )
    parser.add_argument(
        "--variant",
        choices=list(ALL_VARIANT_IDS),
        help="Run a single variant (default: all variants for the protocol)",
    )
    duration = parser.add_mutually_exclusive_group()
    duration.add_argument(
        "--turns",
        type=int,
        default=None,
        help=f"Ticks to advance (default: 10 = {DEFAULT_TURNS * DEFAULT_YEARS_PER_TURN} years)",
    )
    duration.add_argument(
        "--years",
        type=int,
        default=None,
        help=f"Simulated years to advance (must be multiple of {DEFAULT_YEARS_PER_TURN}; e.g. 100, 200)",
    )
    parser.add_argument("--seed", type=int, default=EXPERIMENT_SEED)
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=f"Calendar start year AD (default: {DEFAULT_START_YEAR})",
    )
    parser.add_argument(
        "--run",
        metavar="ID",
        help="Run folder under result/raw/ (e.g. run-002, run2-001, or 2). Default: auto next in --series",
    )
    parser.add_argument(
        "--series",
        default="run",
        help="Run id prefix when --run is omitted (default: run → run-001). Use run2 for an improved batch",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override output directory (advanced; skips {series}-NNN layout)",
    )
    args = parser.parse_args()

    try:
        validate_series(args.series)
    except ValueError as exc:
        parser.error(str(exc))

    years_per_turn = DEFAULT_YEARS_PER_TURN
    if args.years is not None:
        if args.years <= 0 or args.years % years_per_turn != 0:
            parser.error(f"--years must be a positive multiple of {years_per_turn}")
        turns = args.years // years_per_turn
    else:
        turns = DEFAULT_TURNS if args.turns is None else args.turns
    if turns <= 0:
        parser.error("--turns must be positive")

    if args.variant:
        variants = [args.variant]
        try:
            protocol = protocol_for_variant(args.variant)
        except ValueError:
            protocol = args.protocol
    else:
        protocol = args.protocol
        variants = list(variant_ids_for_protocol(protocol))
    raw_root = ROOT / "result" / "raw"
    if args.out_dir is not None:
        out_dir = args.out_dir
        run_id = None
    else:
        out_dir, run_id = resolve_run_dir(raw_root, args.run, series=args.series)
    out_dir.mkdir(parents=True, exist_ok=True)

    llm = describe_provider()
    milestone_years = turns * years_per_turn
    end_year = args.start_year + milestone_years
    print(
        f"Controlled experiment [{protocol}] — seed={args.seed}, "
        f"AD {args.start_year} → AD {end_year} ({milestone_years} years, {turns} turns), "
        f"LLM={llm.get('provider')} (wired={llm.get('wired')})",
    )
    if llm.get("provider") == "ollama":
        observe = llm.get("ollama_model")
        decide = llm.get("ollama_model_decision") or observe
        extra = f" observe={observe} decide={decide}" if decide != observe else f" {observe}"
        print(f"  Ollama:{extra} @ {get_settings().ollama_base_url}")
    if run_id:
        print(f"  Run: {run_id} → {relative_repo_path(out_dir, ROOT)}")
    records: list[dict] = []

    for variant in variants:
        print(f"  → {variant} ({variant_label_ja(variant)}) ...", flush=True)
        params = world_params_for_variant(variant, args.seed, args.start_year)
        roster = fresh_roster_copy(args.seed)
        sim_id = str(uuid.uuid4())
        sim = create_simulation(sim_id, params, agent_roster=roster)
        prepare_experiment_sim(sim, variant=variant, seed=args.seed, total_turns=turns)
        tick(sim, n=turns)
        summary = experiment_summary(sim)
        report = build_report(sim, summary, run_id=run_id)
        filename = _export_filename(variant, _calendar_year(sim), sim.world.turn)
        out_path = out_dir / filename
        out_path.write_text(report, encoding="utf-8")
        json_name = filename.replace(".txt", ".json")
        run_rel = relative_repo_path(out_dir, ROOT)
        json_payload = {
            "format": "civ-experiment-result-v1",
            "run_id": run_id,
            "protocol": protocol,
            "variant": variant,
            "variant_label_ja": variant_label_ja(variant),
            "experiment_seed": args.seed,
            "start_year": args.start_year,
            "years_per_turn": years_per_turn,
            "milestone_turn": sim.world.turn,
            "milestone_years": milestone_years,
            "simulation_id": sim_id,
            "turn": sim.world.turn,
            "calendar_year": _calendar_year(sim),
            "shock_pulse_turns": list(sim.shock_pulse_turns or []),
            "llm": llm,
            "experiment_summary": summary,
            "report_txt": f"{run_rel}/{filename}",
        }
        json_path = out_dir / json_name
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

    if run_id:
        update_manifest(
            out_dir,
            run_id,
            records,
            experiment_seed=args.seed,
            start_year=args.start_year,
            years_per_turn=years_per_turn,
            milestone_turn=turns,
            protocol=protocol,
        )
        analysis_dir = analysis_run_dir(ROOT, run_id)
        print(f"\nDone. {len(records)} report(s) in {out_dir}")
        print(f"Analysis: {relative_repo_path(analysis_dir, ROOT)}/ （comparison・summary 等を配置）")
    else:
        print(f"\nDone. {len(records)} report(s) in {out_dir}")
    if run_id:
        print(f"Next: analysis/prompt.md で LLM 比較 → analysis/output/{run_id}/ に保存")
    else:
        print("Next: analysis/prompt.md で LLM 比較 → analysis/output/run-NNN/ に保存")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
