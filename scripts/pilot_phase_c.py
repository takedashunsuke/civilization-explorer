#!/usr/bin/env python3
"""Phase C pilot: same shock column × different social structures (resilience protocol).

Usage:
  backend\\.venv\\Scripts\\python.exe scripts\\pilot_phase_c.py
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
    RESILIENCE_VARIANT_IDS,
    experiment_summary,
    fresh_roster_copy,
    prepare_experiment_sim,
    variant_label_ja,
    world_params_for_variant,
)

SEED = 42
TURNS = 10


def main() -> int:
    print(f"Phase C pilot | protocol=resilience | seed={SEED} | turns={TURNS} | LLM=stub")
    rows: list[dict] = []
    t0 = time.time()
    pulse_ref: list[int] | None = None
    shock_counts: list[int] = []

    for variant in RESILIENCE_VARIANT_IDS:
        params = world_params_for_variant(variant, SEED, start_year=1750)
        sim = create_simulation(f"pilot-c-{variant}", params, agent_roster=fresh_roster_copy(SEED))
        prepare_experiment_sim(sim, variant=variant, seed=SEED, total_turns=TURNS)
        if pulse_ref is None:
            pulse_ref = list(sim.shock_pulse_turns)
        tick(sim, n=TURNS)
        summary = experiment_summary(sim)
        rows.append(summary)
        shock_counts.append(int(summary.get("shock_count") or 0))
        print(
            f"  {variant:9} ({variant_label_ja(variant)}) "
            f"alive={summary['population_alive']:4}  retain={summary['pop_retention_ratio']}  "
            f"recovery={summary['pop_recovery_ratio']}  "
            f"shocks={summary['shock_count']}  deaths_d={summary['disaster_deaths']}  "
            f"coop_ratio={summary['coop_vs_conflict_post_shock']}  "
            f"break={summary['regime_break']}  label={summary['resilience_label']}"
        )

    print(f"\npulse turns: {pulse_ref}")
    print(f"elapsed={time.time() - t0:.1f}s")

    alives = [r["population_alive"] for r in rows]
    retains = [r["pop_retention_ratio"] for r in rows]
    spread = max(alives) - min(alives)
    retain_spread = max(retains) - min(retains)
    # Same crisis environment: shock counts should be close (pulse + shared shock RNG).
    shock_spread = max(shock_counts) - min(shock_counts)

    ok_pulse = pulse_ref == [2, 5, 8]
    ok_social_split = spread >= 20 or retain_spread >= 0.02
    ok_shock_similar = shock_spread <= max(6, int(0.35 * max(shock_counts)))
    ok_metrics = all(r.get("pop_retention_ratio") is not None for r in rows)

    print("Acceptance:")
    print(f"  pulse schedule [2,5,8]: {pulse_ref} -> {'PASS' if ok_pulse else 'FAIL'}")
    print(
        f"  social divergence (alive spread>={20} or retain spread>=0.02): "
        f"alive_spread={spread}, retain_spread={retain_spread:.3f} -> "
        f"{'PASS' if ok_social_split else 'FAIL'}"
    )
    print(
        f"  shock counts similar (spread<={max(6, int(0.35 * max(shock_counts)))}): "
        f"{shock_counts} spread={shock_spread} -> {'PASS' if ok_shock_similar else 'FAIL'}"
    )
    print(f"  resilience metrics present: {'PASS' if ok_metrics else 'FAIL'}")

    if ok_pulse and ok_social_split and ok_shock_similar and ok_metrics:
        print("\nPhase C pilot: OK")
        return 0
    print("\nPhase C pilot: needs tuning")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
