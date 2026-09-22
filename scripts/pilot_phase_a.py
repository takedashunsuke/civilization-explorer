#!/usr/bin/env python3
"""Phase A/B pilot: population divergence + resilience metrics.

Usage (from repo root, stub LLM):
  backend\\.venv\\Scripts\\python.exe scripts\\pilot_phase_a.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

os.environ["LLM_PROVIDER"] = "stub"

from simulation import create_simulation, tick  # noqa: E402
from simulation.experiment import (  # noqa: E402
    WORLD_VARIANT_IDS,
    _VARIANT_LABEL_JA,
    experiment_summary,
    fresh_roster_copy,
    world_params_for_variant,
)

SEED = 42
TURNS = 10


def main() -> int:
    print(f"Phase A/B pilot | seed={SEED} | turns={TURNS} | LLM=stub")
    rows: list[dict] = []
    t0 = time.time()
    for variant in WORLD_VARIANT_IDS:
        params = world_params_for_variant(variant, SEED, start_year=1750)
        sim = create_simulation(f"pilot-{variant}", params, agent_roster=fresh_roster_copy(SEED))
        sim.experiment_variant = variant
        tick(sim, n=TURNS)
        summary = experiment_summary(sim)
        rows.append({"variant": variant, **summary})
        print(
            f"  {variant:9} alive={summary['population_alive']:4}  "
            f"trough={summary['pop_trough']}  retain={summary['pop_retention_ratio']}  "
            f"recovery={summary['pop_recovery_ratio']}  "
            f"res={summary['resource_pool']}  half_t={summary['resource_recovery_halftime']}  "
            f"shocks={summary['shock_count']}  deaths_d={summary['disaster_deaths']}  "
            f"age={summary.get('age_deaths')}  shock_d={summary.get('shock_attributed_deaths')}  "
            f"share={summary.get('shock_death_share')}  mort={summary.get('shock_mortality_ratio')}  "
            f"break={summary['regime_break']}  label={summary['resilience_label']}"
        )

    by_id = {r["variant"]: r for r in rows}
    lush = by_id["lush"]["population_alive"]
    lean = by_id["lean"]["population_alive"]
    volatile = by_id["volatile"]["population_alive"]
    balanced = by_id["balanced"]["population_alive"]

    print(f"\nelapsed={time.time() - t0:.1f}s")
    print("Acceptance:")
    ok_vol = volatile < lush
    ok_lean_res = (by_id["lean"]["resource_pool"] or 0) < (by_id["lush"]["resource_pool"] or 0)
    spread = max(r["population_alive"] for r in rows) - min(r["population_alive"] for r in rows)
    ok_spread = spread >= 30
    ok_metrics = all(
        r.get("pop_trough") is not None and r.get("pop_recovery_ratio") is not None for r in rows
    )
    labels = {r["variant"]: r["resilience_label"] for r in rows}
    print(f"  volatile alive < lush: {volatile} < {lush} -> {'PASS' if ok_vol else 'FAIL'}")
    print(
        f"  lean resource < lush: {by_id['lean']['resource_pool']} < {by_id['lush']['resource_pool']} -> "
        f"{'PASS' if ok_lean_res else 'FAIL'}"
    )
    print(f"  alive spread >= 30: {spread} -> {'PASS' if ok_spread else 'FAIL'}")
    print(f"  resilience metrics present: {'PASS' if ok_metrics else 'FAIL'}")
    print(f"  labels: {labels}")
    print(f"  balanced alive={balanced} lean alive={lean}")

    if ok_vol and ok_lean_res and ok_spread and ok_metrics:
        print("\nPhase A/B pilot: OK")
        return 0
    print("\nPhase A/B pilot: needs tuning")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
