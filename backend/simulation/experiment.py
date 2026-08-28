"""Controlled experiment: identical agent roster × different world environments."""

from __future__ import annotations

from typing import Any

from simulation.continents import CONTINENT_IDS, DEFAULT_SUBREGION
from simulation.engine import clone_roster_for_world, generate_agent_roster
from simulation.models import (
    AgentState,
    GeographyType,
    InitialValues,
    InstitutionType,
    RegionParams,
    ReligionType,
    SimulationState,
    WorldParams,
)

EXPERIMENT_SEED = 42
EXPERIMENT_POPULATION_PER_REGION = 1000

WORLD_VARIANT_IDS: tuple[str, ...] = ("peace", "famine", "war", "trade")

# Environment-only patches. Identity fields (initial_values, trait_rate, population) stay fixed.
_ENV_PATCH: dict[str, dict[str, float | str]] = {
    "peace": {
        "resource_pool": 145.0,
        "disaster_frequency": 0.07,
        "institution": "democracy",
        "tax_rate": 0.06,
        "trade_openness": 0.78,
        "welfare_rate": 0.18,
    },
    "famine": {
        "resource_pool": 38.0,
        "disaster_frequency": 0.50,
        "institution": "autocracy",
        "tax_rate": 0.22,
        "trade_openness": 0.20,
        "welfare_rate": 0.02,
    },
    "war": {
        "resource_pool": 62.0,
        "disaster_frequency": 0.38,
        "institution": "autocracy",
        "tax_rate": 0.26,
        "trade_openness": 0.25,
        "welfare_rate": 0.04,
    },
    "trade": {
        "resource_pool": 128.0,
        "disaster_frequency": 0.10,
        "institution": "democracy",
        "tax_rate": 0.07,
        "trade_openness": 0.92,
        "welfare_rate": 0.14,
    },
}

_VARIANT_LABEL_JA: dict[str, str] = {
    "peace": "平和・豊富",
    "famine": "飢饉・災害",
    "war": "戦争・緊張",
    "trade": "交易・開放",
}

_ROSTER_CACHE: dict[int, list[AgentState]] = {}


def baseline_identity_values() -> InitialValues:
    return InitialValues(
        cooperation=0.5,
        authority_acceptance=0.5,
        ambition=0.5,
        inequality=0.5,
    )


def baseline_region_params() -> list[RegionParams]:
    """Uniform identity baseline — used only to generate the shared roster."""
    identity = baseline_identity_values()
    out: list[RegionParams] = []
    for macro in CONTINENT_IDS:
        out.append(
            RegionParams(
                id=macro,
                subregion_id=DEFAULT_SUBREGION[macro],
                population=EXPERIMENT_POPULATION_PER_REGION,
                institution=InstitutionType.democracy,
                tax_rate=0.1,
                education_level=0.5,
                religion=ReligionType.folk,
                trade_openness=0.5,
                initial_values=identity,
                trait_rate=0.1,
                welfare_rate=0.0,
            )
        )
    return out


def region_params_for_variant(variant: str) -> list[RegionParams]:
    if variant not in _ENV_PATCH:
        raise ValueError(f"unknown experiment variant: {variant}")
    patch = _ENV_PATCH[variant]
    inst = InstitutionType(str(patch["institution"]))
    identity = baseline_identity_values()
    out: list[RegionParams] = []
    for macro in CONTINENT_IDS:
        out.append(
            RegionParams(
                id=macro,
                subregion_id=DEFAULT_SUBREGION[macro],
                population=EXPERIMENT_POPULATION_PER_REGION,
                institution=inst,
                tax_rate=float(patch["tax_rate"]),
                education_level=0.5,
                religion=ReligionType.folk,
                trade_openness=float(patch["trade_openness"]),
                initial_values=identity,
                trait_rate=0.1,
                welfare_rate=float(patch["welfare_rate"]),
                resource_pool=float(patch["resource_pool"]),
                disaster_frequency=float(patch["disaster_frequency"]),
            )
        )
    return out


def world_params_for_variant(variant: str, seed: int, start_year: int = 1000) -> WorldParams:
    return WorldParams(
        seed=seed,
        population=EXPERIMENT_POPULATION_PER_REGION,
        start_year=start_year,
        geography=GeographyType.world,
        regions=region_params_for_variant(variant),
    )


def get_experiment_roster(seed: int) -> list[AgentState]:
    if seed not in _ROSTER_CACHE:
        _ROSTER_CACHE[seed] = generate_agent_roster(baseline_region_params(), seed)
    return _ROSTER_CACHE[seed]


def fresh_roster_copy(seed: int) -> list[AgentState]:
    return clone_roster_for_world(get_experiment_roster(seed))


def describe_experiment() -> dict[str, Any]:
    total = EXPERIMENT_POPULATION_PER_REGION * len(CONTINENT_IDS)
    return {
        "seed": EXPERIMENT_SEED,
        "population_per_region": EXPERIMENT_POPULATION_PER_REGION,
        "total_agents": total,
        "fixed": [
            "agent_id",
            "personality",
            "traits",
            "initial_position",
            "initial_population",
            "seed",
        ],
        "varied": [
            "resource_pool",
            "disaster_frequency",
            "institution",
            "tax_rate",
            "trade_openness",
            "welfare_rate",
        ],
        "variants": [
            {
                "id": vid,
                "label_ja": _VARIANT_LABEL_JA[vid],
                "env": _ENV_PATCH[vid],
            }
            for vid in WORLD_VARIANT_IDS
        ],
    }


def experiment_summary(sim: SimulationState) -> dict[str, Any]:
    alive = [a for a in sim.agents if a.alive]
    initial = sim.world.initial_population or len(sim.agents)
    pop_delta_pct = round((len(alive) - initial) / max(initial, 1) * 100, 1)
    conflicts = sum(1 for e in sim.events if e.action.value == "conflict")
    cooperations = sum(1 for e in sim.events if e.action.value == "cooperate")
    regime_shifts = sum(1 for e in sim.events if e.action.value == "regime")
    disasters = sum(1 for e in sim.events if e.action.value == "disaster")

    trade_open = 0.0
    if sim.world.regions:
        trade_open = sum(r.trade_openness for r in sim.world.regions) / len(sim.world.regions)

    resource_start = sum(
        r.resource_pool for r in sim.world.regions
    )  # post-tick value; initial not stored per-region
    resource_now = sum(r.resource_pool for r in sim.world.regions)

    archetypes: list[str] = []
    trajectories: list[str] = []
    if sim.region_readings:
        for reading in sim.region_readings:
            if reading.rising_archetype and reading.rising_archetype != "none":
                archetypes.append(reading.rising_archetype)
            if reading.trajectory and reading.trajectory != "stagnation":
                trajectories.append(reading.trajectory)

    institutions = [r.institution.value for r in sim.world.regions]
    dominant_archetype = archetypes[0] if archetypes else "none"
    if archetypes:
        counts: dict[str, int] = {}
        for a in archetypes:
            counts[a] = counts.get(a, 0) + 1
        dominant_archetype = max(counts, key=counts.get)

    leaders = {s.leader_id for s in sim.settlements if s.leader_id}
    spotlight = _pick_spotlight_agent(sim, leaders)

    return {
        "variant": sim.experiment_variant,
        "variant_label_ja": _VARIANT_LABEL_JA.get(sim.experiment_variant or "", ""),
        "seed": sim.experiment_seed or sim.world.seed,
        "turn": sim.world.turn,
        "calendar_year": sim.world.start_year + sim.world.turn * sim.world.years_per_turn,
        "population_alive": len(alive),
        "population_delta_pct": pop_delta_pct,
        "resource_pool": round(resource_now, 1),
        "trade_openness_mean": round(trade_open, 2),
        "conflicts_total": conflicts,
        "cooperations_total": cooperations,
        "regime_shifts": regime_shifts,
        "disasters": disasters,
        "dominant_archetype": dominant_archetype,
        "archetypes": archetypes,
        "trajectories": trajectories,
        "institutions": institutions,
        "spotlight_agent_id": spotlight.id if spotlight else None,
        "spotlight_role": _agent_role_label(sim, spotlight) if spotlight else None,
    }


def _pick_spotlight_agent(sim: SimulationState, leaders: set[str]) -> AgentState | None:
    """Prefer a leader with charisma; else any leader; else highest ambition alive."""
    alive = [a for a in sim.agents if a.alive]
    leader_agents = [a for a in alive if a.id in leaders]
    if leader_agents:
        charisma_leaders = [a for a in leader_agents if "charisma" in a.traits]
        pool = charisma_leaders or leader_agents
        return max(pool, key=lambda a: a.personality.ambition + a.personality.aggression)
    if alive:
        return max(alive, key=lambda a: a.personality.ambition + len(a.traits) * 0.2)
    return None


def _agent_role_label(sim: SimulationState, agent: AgentState) -> str:
    leaders = {s.leader_id for s in sim.settlements if s.leader_id}
    if agent.id in leaders:
        region = agent.subregion_id or agent.region_id
        for reading in sim.region_readings:
            rid = reading.subregion_id or reading.region_id
            if rid == region and reading.rising_archetype != "none":
                return reading.rising_archetype
        return "leader"
    return "citizen"
