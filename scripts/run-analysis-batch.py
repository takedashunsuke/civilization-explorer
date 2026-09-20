#!/usr/bin/env python3
"""Generate analysis/output/run-NNN/ from completed result/raw runs.

Usage (from repo root):
  ./scripts/run-analysis-batch.sh              # quant tables for all complete runs
  ./scripts/run-analysis-batch.sh --llm        # + Ollama qualitative (slow)
  ./scripts/run-analysis-batch.sh --run 3      # single run-003
  ./scripts/run-analysis-batch.sh --series run2 # improved batch only
  ./scripts/run-analysis-batch.sh --from-run 5 # run-005 … latest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "backend"))

from analysis_batch import (  # noqa: E402
    build_cross_run_markdown,
    complete_run_entries,
    load_result_manifest,
    process_run,
)
from experiment_runs import normalize_run_id, parse_run_id, validate_series  # noqa: E402


def filter_runs(
    runs: list[dict],
    *,
    run_id: str | None,
    from_run: str | None,
    series: str | None,
) -> list[dict]:
    if series:
        series = validate_series(series)
        runs = [r for r in runs if _series_of(r.get("id", "")) == series]
    if run_id:
        rid = normalize_run_id(run_id, series=series or "run")
        matched = [r for r in runs if r.get("id") == rid]
        if not matched:
            raise SystemExit(f"run not found or incomplete: {rid}")
        return matched
    if from_run:
        start = normalize_run_id(from_run, series=series or "run")
        return [r for r in runs if r.get("id", "") >= start]
    return runs


def _series_of(run_id: str) -> str:
    try:
        name, _ = parse_run_id(run_id)
        return name
    except ValueError:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch analysis for experiment runs")
    parser.add_argument("--run", metavar="ID", help="Single run (e.g. run-003, run2-001, or 3)")
    parser.add_argument("--from-run", metavar="ID", help="From this run through latest")
    parser.add_argument(
        "--series",
        metavar="NAME",
        help="Only this series (e.g. run2). Bare --run 1 then means run2-001",
    )
    parser.add_argument("--llm", action="store_true", help="Call Ollama for qualitative sections")
    parser.add_argument("--force", action="store_true", help="Overwrite existing comparison/summary")
    parser.add_argument("--aggregate", action="store_true", help="Write analysis/output/cross-run-summary.md")
    parser.add_argument("--dry-run", action="store_true", help="List targets only")
    args = parser.parse_args()

    if args.series:
        try:
            validate_series(args.series)
        except ValueError as exc:
            parser.error(str(exc))

    manifest = load_result_manifest(ROOT)
    runs = complete_run_entries(manifest)
    runs = filter_runs(runs, run_id=args.run, from_run=args.from_run, series=args.series)

    if not runs:
        print("No complete runs found in result/manifest.json")
        return 1

    print(f"Analysis batch — {len(runs)} run(s)" + (" + LLM" if args.llm else " (quant only)"))
    for run in runs:
        print(f"  · {run['id']} seed={run.get('experiment_seed')}")

    if args.dry_run:
        return 0

    for run in runs:
        process_run(ROOT, run, use_llm=args.llm, force=args.force)

    if args.aggregate and len(runs) >= 2:
        from datetime import date

        day = date.today().isoformat()
        out = ROOT / "analysis" / "output" / f"cross-run-summary-{day}.md"
        out.write_text(build_cross_run_markdown(ROOT, runs, day), encoding="utf-8")
        print(f"\nAggregate: {out.relative_to(ROOT)}")

    print("\nDone. See analysis/output/ and analysis/summary.md index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
