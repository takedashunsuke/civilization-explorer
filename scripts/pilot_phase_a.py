#!/usr/bin/env python3
"""Phase A pilot: same roster × 4 variants; check population / resource divergence.

Usage (from repo root, stub LLM):
  cd backend && .venv/Scripts/python.exe ../scripts/pilot_phase_a.py
  # or
  ./scripts/pilot_phase_a.sh
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Force heuristic path — Phase A must diverge without LLM.
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
TURNS = 10  # 100 years at 10y/turn — enough to see demography split


def main() -> int:
    print(f"Phase A pilot | seed={SEED} | turns={TURNS} | LLM=stub")
    rows: list[dict] = []
    t0 = time.time()
    for variant in WORLD_VARIANT_IDS:
        params = world_params_for_variant(variant, SEED, start_year=1750)
        sim = create_simulation(f"pilot-{variant}", params, agent_roster=fresh_roster_copy(SEED))
        sim.experiment_variant = variant
        tick(sim, n=TURNS)
        summary = experiment_summary(sim)
        alive = sum(1 for a in sim.agents if a.alive)
        disaster_deaths = sum(
            1 for e in sim.events if e.action.value == "death" and e.detail_key == "death_disaster"
        )
        rows.append(
            {
                "variant": variant,
                "label": _VARIANT_LABEL_JA[variant],
                "alive": alive,
                "pop_delta_pct": summary.get("population_delta_pct"),
                "resource": summary.get("resource_pool"),
                "disasters": summary.get("disasters"),
                "disaster_deaths": disaster_deaths,
            }
        )
        print(
            f"  {variant:9} alive={alive:4}  Δpop%={summary.get('population_delta_pct')}  "
            f"resource={summary.get('resource_pool')}  disasters={summary.get('disasters')}  "
            f"disaster_deaths={disaster_deaths}"
        )

    by_id = {r["variant"]: r for r in rows}
    lush = by_id["lush"]["alive"]
    lean = by_id["lean"]["alive"]
    volatile = by_id["volatile"]["alive"]
    balanced = by_id["balanced"]["alive"]

    print(f"\nelapsed={time.time() - t0:.1f}s")
    print("Acceptance (soft):")
    ok_vol = volatile < lush
    ok_lean_res = (by_id["lean"]["resource"] or 0) < (by_id["lush"]["resource"] or 0)
    spread = max(r["alive"] for r in rows) - min(r["alive"] for r in rows)
    ok_spread = spread >= 30
    print(f"  volatile alive < lush: {volatile} < {lush} → {'PASS' if ok_vol else 'FAIL'}")
    print(
        f"  lean resource < lush: {by_id['lean']['resource']} < {by_id['lush']['resource']} → "
        f"{'PASS' if ok_lean_res else 'FAIL'}"
    )
    print(f"  alive spread ≥ 30: {spread} → {'PASS' if ok_spread else 'FAIL'}")
    print(f"  balanced alive={balanced} lean alive={lean}")

    if ok_vol and ok_lean_res and ok_spread:
        print("\nPhase A pilot: OK")
        return 0
    print("\nPhase A pilot: needs tuning")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
