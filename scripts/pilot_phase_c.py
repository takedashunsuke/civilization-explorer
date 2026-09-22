#!/usr/bin/env python3
"""Phase C pilot: same shock column × different social structures (resilience protocol).

Usage:
  backend/.venv/bin/python scripts/pilot_phase_c.py
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
from simulation.models import ActionType  # noqa: E402
from simulation.shocks import shock_plan_signature  # noqa: E402

SEED = 42
TURNS = 10
_WEALTH_ORDER = ("commune", "civic", "autocrat", "fracture")


def _wealth_std(agents) -> float:
    xs = [a.wealth for a in agents if a.alive]
    mean = sum(xs) / len(xs)
    return (sum((x - mean) ** 2 for x in xs) / len(xs)) ** 0.5


def _wealth_rank(agents) -> tuple[str, ...]:
    return tuple(a.id for a in sorted(agents, key=lambda x: (round(x.wealth, 6), x.id)))


def _emitted_column(sim) -> list[tuple[int, str, str]]:
    """Disaster events only (not deaths). Identity of the crisis column."""
    out: list[tuple[int, str, str]] = []
    for e in sim.events:
        if e.action != ActionType.disaster:
            continue
        out.append((int(e.turn), str(e.actor_id), str(e.detail_key)))
    return out


def main() -> int:
    print(f"Phase C pilot | protocol=resilience | seed={SEED} | turns={TURNS} | LLM=stub")
    rows: list[dict] = []
    t0 = time.time()
    pulse_ref: list[int] | None = None
    plan_ref: list[tuple[int, str, str]] | None = None
    emitted: list[list[tuple[int, str, str]]] = []
    shock_counts: list[int] = []
    wealth_std: dict[str, float] = {}
    rank_ref: tuple[str, ...] | None = None
    rank_ok = True

    for variant in RESILIENCE_VARIANT_IDS:
        params = world_params_for_variant(variant, SEED, start_year=1750)
        sim = create_simulation(f"pilot-c-{variant}", params, agent_roster=fresh_roster_copy(SEED))
        prepare_experiment_sim(sim, variant=variant, seed=SEED, total_turns=TURNS)
        wealth_std[variant] = _wealth_std(sim.agents)
        ranks = _wealth_rank(sim.agents)
        if rank_ref is None:
            rank_ref = ranks
        elif ranks != rank_ref:
            rank_ok = False
        if pulse_ref is None:
            pulse_ref = list(sim.shock_pulse_turns)
        sig = shock_plan_signature(list(sim.shock_plan or []))
        if plan_ref is None:
            plan_ref = sig
        elif sig != plan_ref:
            print(f"  PLAN MISMATCH on {variant}")
        tick(sim, n=TURNS)
        summary = experiment_summary(sim)
        rows.append(summary)
        shock_counts.append(int(summary.get("shock_count") or 0))
        emitted.append(_emitted_column(sim))
        print(
            f"  {variant:9} ({variant_label_ja(variant)}) "
            f"alive={summary['population_alive']:4}  retain={summary['pop_retention_ratio']}  "
            f"recovery={summary['pop_recovery_ratio']}  "
            f"shocks={summary['shock_count']}  deaths_d={summary['disaster_deaths']}  "
            f"plan={summary.get('shock_plan_len')}  "
            f"coop_ratio={summary['coop_vs_conflict_post_shock']}  "
            f"break={summary['regime_break']}  label={summary['resilience_label']}"
        )

    print(f"\npulse turns: {pulse_ref}")
    print(f"plan events: {len(plan_ref or [])}")
    print(f"elapsed={time.time() - t0:.1f}s")

    alives = [r["population_alive"] for r in rows]
    retains = [r["pop_retention_ratio"] for r in rows]
    spread = max(alives) - min(alives)
    retain_spread = max(retains) - min(retains)
    shock_spread = max(shock_counts) - min(shock_counts)

    ok_pulse = pulse_ref == [2, 5, 8]
    ok_plan = all(r.get("shock_plan_signature") == rows[0].get("shock_plan_signature") for r in rows)
    ok_emitted = all(col == emitted[0] for col in emitted)
    ok_shock_equal = shock_spread == 0
    ok_social_split = spread >= 20 or retain_spread >= 0.02
    ok_metrics = all(r.get("pop_retention_ratio") is not None for r in rows)
    ordered_std = [wealth_std[v] for v in _WEALTH_ORDER]
    ok_wealth_spread = all(ordered_std[i] < ordered_std[i + 1] for i in range(len(ordered_std) - 1))

    print("Acceptance:")
    print(f"  pulse schedule [2,5,8]: {pulse_ref} -> {'PASS' if ok_pulse else 'FAIL'}")
    print(f"  shock_plan identical: {'PASS' if ok_plan else 'FAIL'}")
    print(
        f"  emitted disaster column identical: "
        f"{'PASS' if ok_emitted else 'FAIL'} (len={len(emitted[0]) if emitted else 0})"
    )
    print(
        f"  shock counts equal: {shock_counts} spread={shock_spread} -> "
        f"{'PASS' if ok_shock_equal else 'FAIL'}"
    )
    print(
        f"  social divergence (alive spread>={20} or retain spread>=0.02): "
        f"alive_spread={spread}, retain_spread={retain_spread:.3f} -> "
        f"{'PASS' if ok_social_split else 'FAIL'}"
    )
    print(f"  resilience metrics present: {'PASS' if ok_metrics else 'FAIL'}")
    print(
        "  initial wealth std commune<civic<autocrat<fracture: "
        + ", ".join(f"{v}={wealth_std[v]:.3f}" for v in _WEALTH_ORDER)
        + f" -> {'PASS' if ok_wealth_spread else 'FAIL'}"
    )
    print(f"  wealth rank preserved across variants: {'PASS' if rank_ok else 'FAIL'}")

    if (
        ok_pulse
        and ok_plan
        and ok_emitted
        and ok_shock_equal
        and ok_social_split
        and ok_metrics
        and ok_wealth_spread
        and rank_ok
    ):
        print("\nPhase C pilot: OK")
        return 0
    print("\nPhase C pilot: needs tuning")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
