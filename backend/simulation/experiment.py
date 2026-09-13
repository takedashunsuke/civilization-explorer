"""Controlled experiments: environment knobs (Phase A/B) and resilience protocol (Phase C)."""

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

PROTOCOL_ENVIRONMENT = "environment"
PROTOCOL_RESILIENCE = "resilience"

WORLD_VARIANT_IDS: tuple[str, ...] = ("lush", "lean", "volatile", "balanced")
RESILIENCE_VARIANT_IDS: tuple[str, ...] = ("civic", "autocrat", "commune", "fracture")
ALL_VARIANT_IDS: tuple[str, ...] = WORLD_VARIANT_IDS + RESILIENCE_VARIANT_IDS

# External environment only — institutions, tax, trade, welfare start neutral and may emerge.
_EXTERNAL_PATCH: dict[str, dict[str, float]] = {
    "lush": {"resource_pool": 145.0, "disaster_frequency": 0.07},
    "lean": {"resource_pool": 42.0, "disaster_frequency": 0.22},
    "volatile": {"resource_pool": 78.0, "disaster_frequency": 0.48},
    "balanced": {"resource_pool": 95.0, "disaster_frequency": 0.16},
}

# Shared crisis environment for resilience protocol (same shock column across social variants).
_RESILIENCE_ENV: dict[str, float] = {
    "resource_pool": 85.0,
    "disaster_frequency": 0.35,
}

_VARIANT_LABEL_JA: dict[str, str] = {
    "lush": "豊かな自然",
    "lean": "資源乏しい",
    "volatile": "災害が多い",
    "balanced": "標準",
    "civic": "民主・協調",
    "autocrat": "専制・秩序",
    "commune": "高福祉・共同",
    "fracture": "無政府・分断",
}

# Social structure knobs for Phase C (environment fixed to _RESILIENCE_ENV).
_RESILIENCE_SOCIAL: dict[str, dict[str, Any]] = {
    "civic": {
        "institution": InstitutionType.democracy,
        "tax_rate": 0.12,
        "education_level": 0.55,
        "religion": ReligionType.secular,
        "trade_openness": 0.55,
        "welfare_rate": 0.16,
        "initial_values": InitialValues(
            cooperation=0.72,
            authority_acceptance=0.58,
            ambition=0.45,
            inequality=0.32,
        ),
    },
    "autocrat": {
        "institution": InstitutionType.autocracy,
        "tax_rate": 0.18,
        "education_level": 0.5,
        "religion": ReligionType.organized,
        "trade_openness": 0.4,
        "welfare_rate": 0.06,
        "initial_values": InitialValues(
            cooperation=0.38,
            authority_acceptance=0.82,
            ambition=0.55,
            inequality=0.55,
        ),
    },
    "commune": {
        "institution": InstitutionType.democracy,
        "tax_rate": 0.22,
        "education_level": 0.52,
        "religion": ReligionType.folk,
        "trade_openness": 0.45,
        "welfare_rate": 0.28,
        "initial_values": InitialValues(
            cooperation=0.8,
            authority_acceptance=0.5,
            ambition=0.4,
            inequality=0.22,
        ),
    },
    "fracture": {
        "institution": InstitutionType.anarchy,
        "tax_rate": 0.02,
        "education_level": 0.45,
        "religion": ReligionType.folk,
        "trade_openness": 0.35,
        "welfare_rate": 0.0,
        "initial_values": InitialValues(
            cooperation=0.25,
            authority_acceptance=0.22,
            ambition=0.72,
            inequality=0.7,
        ),
    },
}

_ROSTER_CACHE: dict[int, list[AgentState]] = {}


def variant_label_ja(variant: str) -> str:
    return _VARIANT_LABEL_JA.get(variant, variant)


def protocol_for_variant(variant: str) -> str:
    if variant in RESILIENCE_VARIANT_IDS:
        return PROTOCOL_RESILIENCE
    if variant in WORLD_VARIANT_IDS:
        return PROTOCOL_ENVIRONMENT
    raise ValueError(f"unknown experiment variant: {variant}")


def variant_ids_for_protocol(protocol: str) -> tuple[str, ...]:
    p = (protocol or PROTOCOL_ENVIRONMENT).strip().lower()
    if p == PROTOCOL_RESILIENCE:
        return RESILIENCE_VARIANT_IDS
    if p == PROTOCOL_ENVIRONMENT:
        return WORLD_VARIANT_IDS
    raise ValueError(f"unknown protocol: {protocol}")


def resilience_pulse_turns(total_turns: int) -> list[int]:
    """Identical forced-crisis turns for the resilience protocol."""
    n = max(1, int(total_turns))
    if n <= 10:
        pulses = (2, 5, 8)
    else:
        pulses = (max(1, int(n * 0.2)), max(2, int(n * 0.5)), max(3, int(n * 0.8)))
    return sorted({t for t in pulses if 0 <= t < n})


def baseline_identity_values() -> InitialValues:
    return InitialValues(
        cooperation=0.5,
        authority_acceptance=0.5,
        ambition=0.5,
        inequality=0.5,
    )


def _neutral_social_baseline() -> dict[str, float | InstitutionType | ReligionType]:
    """No preset society — groups, institutions, and conflict emerge in play."""
    return {
        "institution": InstitutionType.anarchy,
        "tax_rate": 0.05,
        "education_level": 0.5,
        "religion": ReligionType.folk,
        "trade_openness": 0.5,
        "welfare_rate": 0.0,
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def bias_roster_to_identity(agents: list[AgentState], identity: InitialValues) -> None:
    """Shift personalities toward a social bias while keeping relative differences."""
    for agent in agents:
        if not agent.alive:
            continue
        dc = identity.cooperation - 0.5
        da = identity.ambition - 0.5
        agent.personality.cooperation = _clamp01(agent.personality.cooperation + dc)
        agent.personality.ambition = _clamp01(agent.personality.ambition + da)
        agent.personality.aggression = _clamp01(agent.personality.aggression - dc * 0.45)


def baseline_region_params() -> list[RegionParams]:
    """Uniform identity baseline — used only to generate the shared roster."""
    identity = baseline_identity_values()
    social = _neutral_social_baseline()
    out: list[RegionParams] = []
    for macro in CONTINENT_IDS:
        out.append(
            RegionParams(
                id=macro,
                subregion_id=DEFAULT_SUBREGION[macro],
                population=EXPERIMENT_POPULATION_PER_REGION,
                institution=social["institution"],  # type: ignore[arg-type]
                tax_rate=float(social["tax_rate"]),
                education_level=float(social["education_level"]),
                religion=social["religion"],  # type: ignore[arg-type]
                trade_openness=float(social["trade_openness"]),
                initial_values=identity,
                trait_rate=0.1,
                welfare_rate=float(social["welfare_rate"]),
            )
        )
    return out


def region_params_for_variant(variant: str) -> list[RegionParams]:
    if variant in _EXTERNAL_PATCH:
        patch = _EXTERNAL_PATCH[variant]
        identity = baseline_identity_values()
        social = _neutral_social_baseline()
        out: list[RegionParams] = []
        for macro in CONTINENT_IDS:
            out.append(
                RegionParams(
                    id=macro,
                    subregion_id=DEFAULT_SUBREGION[macro],
                    population=EXPERIMENT_POPULATION_PER_REGION,
                    institution=social["institution"],  # type: ignore[arg-type]
                    tax_rate=float(social["tax_rate"]),
                    education_level=float(social["education_level"]),
                    religion=social["religion"],  # type: ignore[arg-type]
                    trade_openness=float(social["trade_openness"]),
                    initial_values=identity,
                    trait_rate=0.1,
                    welfare_rate=float(social["welfare_rate"]),
                    resource_pool=float(patch["resource_pool"]),
                    disaster_frequency=float(patch["disaster_frequency"]),
                )
            )
        return out

    if variant in _RESILIENCE_SOCIAL:
        social = _RESILIENCE_SOCIAL[variant]
        identity = social["initial_values"]
        assert isinstance(identity, InitialValues)
        out = []
        for macro in CONTINENT_IDS:
            out.append(
                RegionParams(
                    id=macro,
                    subregion_id=DEFAULT_SUBREGION[macro],
                    population=EXPERIMENT_POPULATION_PER_REGION,
                    institution=social["institution"],
                    tax_rate=float(social["tax_rate"]),
                    education_level=float(social["education_level"]),
                    religion=social["religion"],
                    trade_openness=float(social["trade_openness"]),
                    initial_values=identity,
                    trait_rate=0.1,
                    welfare_rate=float(social["welfare_rate"]),
                    resource_pool=float(_RESILIENCE_ENV["resource_pool"]),
                    disaster_frequency=float(_RESILIENCE_ENV["disaster_frequency"]),
                )
            )
        return out

    raise ValueError(f"unknown experiment variant: {variant}")


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


def prepare_experiment_sim(
    sim: SimulationState,
    *,
    variant: str,
    seed: int,
    total_turns: int,
) -> None:
    """Mark protocol metadata and apply resilience-only setup (pulse schedule + bias)."""
    protocol = protocol_for_variant(variant)
    sim.controlled_experiment = True
    sim.experiment_variant = variant
    sim.experiment_seed = seed
    sim.experiment_protocol = protocol
    sim.status = "running"
    if protocol == PROTOCOL_RESILIENCE:
        sim.shock_pulse_turns = resilience_pulse_turns(total_turns)
        identity = _RESILIENCE_SOCIAL[variant]["initial_values"]
        assert isinstance(identity, InitialValues)
        bias_roster_to_identity(sim.agents, identity)
    else:
        sim.shock_pulse_turns = []


def apply_variant_to_sim(sim: SimulationState, variant: str) -> None:
    """Update external environment on a running environment-protocol experiment."""
    if variant not in _EXTERNAL_PATCH:
        raise ValueError(f"unknown environment variant: {variant}")
    patch = _EXTERNAL_PATCH[variant]
    for region in sim.world.regions:
        region.resource_pool = float(patch["resource_pool"])
        region.disaster_frequency = float(patch["disaster_frequency"])
    sim.experiment_variant = variant
    sim.experiment_protocol = PROTOCOL_ENVIRONMENT


def describe_experiment() -> dict[str, Any]:
    total = EXPERIMENT_POPULATION_PER_REGION * len(CONTINENT_IDS)
    return {
        "seed": EXPERIMENT_SEED,
        "population_per_region": EXPERIMENT_POPULATION_PER_REGION,
        "total_agents": total,
        "protocols": {
            PROTOCOL_ENVIRONMENT: {
                "label_ja": "環境ノブ（同一人間 × 資源・災害）",
                "fixed": [
                    "agent_id",
                    "personality",
                    "traits",
                    "initial_position",
                    "initial_population",
                    "seed",
                    "starting_institution_anarchy",
                ],
                "varied": ["resource_pool", "disaster_frequency"],
                "variants": [
                    {"id": vid, "label_ja": _VARIANT_LABEL_JA[vid], "env": _EXTERNAL_PATCH[vid]}
                    for vid in WORLD_VARIANT_IDS
                ],
            },
            PROTOCOL_RESILIENCE: {
                "label_ja": "レジリエンス（同一ショック × 社会構造）",
                "fixed": [
                    "agent_id",
                    "traits",
                    "initial_position",
                    "seed",
                    "resource_pool",
                    "disaster_frequency",
                    "shock_pulse_turns",
                ],
                "varied": [
                    "institution",
                    "tax_rate",
                    "welfare_rate",
                    "cooperation_bias",
                    "authority_acceptance",
                ],
                "shared_env": _RESILIENCE_ENV,
                "variants": [
                    {
                        "id": vid,
                        "label_ja": _VARIANT_LABEL_JA[vid],
                        "social": {
                            "institution": _RESILIENCE_SOCIAL[vid]["institution"].value,
                            "tax_rate": _RESILIENCE_SOCIAL[vid]["tax_rate"],
                            "welfare_rate": _RESILIENCE_SOCIAL[vid]["welfare_rate"],
                            "cooperation": _RESILIENCE_SOCIAL[vid]["initial_values"].cooperation,
                        },
                    }
                    for vid in RESILIENCE_VARIANT_IDS
                ],
            },
        },
        "fixed": [
            "agent_id",
            "personality",
            "traits",
            "initial_position",
            "initial_population",
            "seed",
            "starting_institution_anarchy",
        ],
        "varied": [
            "resource_pool",
            "disaster_frequency",
        ],
        "varied_label_ja": [
            "共有資源（resource_pool）",
            "災害（disaster_frequency）",
        ],
        "fixed_background_ja": "舞台: サブ地域・気候・地形・衛生・食の説明（UI叙事。数値はサブ地域プリセット）",
        "not_modeled_ja": [
            "食料・水・木材・石油などの個別資源",
            "時代による重要資源の切り替え",
        ],
        "layers": [
            {
                "id": "stage",
                "label_ja": "① 舞台",
                "fields": ["subregion_id", "climate", "landform", "sanitation", "terrain"],
                "experiment": "fixed_per_column",
            },
            {
                "id": "knobs",
                "label_ja": "② 実験ノブ",
                "fields": ["resource_pool", "disaster_frequency"],
                "experiment": "varied_across_worlds_environment_protocol",
            },
            {
                "id": "roster",
                "label_ja": "③ 人間ロスター",
                "fields": ["agent_id", "personality", "traits", "initial_position"],
                "experiment": "fixed_same_roster",
            },
            {
                "id": "social_initial",
                "label_ja": "③′ 社会の初期値",
                "fields": ["institution", "tax_rate", "education_level", "religion", "trade_openness", "welfare_rate"],
                "experiment": "neutral_or_varied_by_protocol",
            },
            {
                "id": "emergent",
                "label_ja": "④ 創発",
                "fields": ["settlements", "leaders", "conflict", "regime", "wealth", "population"],
                "experiment": "changes_during_play",
            },
        ],
        "docs": "docs/hackathon/world-model.md",
        "docs_post_award": "docs/hackathon/post-award.md",
        "emerges_in_play": [
            "settlements",
            "institutions",
            "conflict",
            "leaders",
        ],
        "variants": [
            {
                "id": vid,
                "label_ja": _VARIANT_LABEL_JA[vid],
                "env": _EXTERNAL_PATCH[vid],
                "protocol": PROTOCOL_ENVIRONMENT,
            }
            for vid in WORLD_VARIANT_IDS
        ]
        + [
            {
                "id": vid,
                "label_ja": _VARIANT_LABEL_JA[vid],
                "env": _RESILIENCE_ENV,
                "protocol": PROTOCOL_RESILIENCE,
            }
            for vid in RESILIENCE_VARIANT_IDS
        ],
    }


AUTHORITY_BREAK_THRESHOLD = 0.35


def compute_resilience_metrics(sim: SimulationState) -> dict[str, Any]:
    """Phase B: recovery-vs-collapse metrics from history + events."""
    alive_now = sum(1 for a in sim.agents if a.alive)
    resource_now = (
        sum(r.resource_pool for r in sim.world.regions)
        if sim.world.regions
        else float(sim.world.resource_pool)
    )
    shock_count = sum(1 for e in sim.events if e.action.value == "disaster")
    disaster_deaths = sum(
        1 for e in sim.events if e.action.value == "death" and e.detail_key == "death_disaster"
    )

    history = list(sim.history)
    # Build per-turn series (fallback-parse older history without numeric fields).
    series: list[dict[str, Any]] = []
    for row in history:
        pop = row.population_alive
        if pop is None:
            # "turn=N pop=X ..."
            pop = alive_now
            parts = row.summary.split()
            for part in parts:
                if part.startswith("pop="):
                    try:
                        pop = int(part.split("=", 1)[1])
                    except ValueError:
                        pass
                    break
        res = row.resource_pool
        if res is None:
            res = resource_now
        auth = row.mean_authority
        if auth is None:
            auth = float(row.metrics.authority) if row.metrics else 0.5
        series.append(
            {
                "turn": row.turn,
                "population_alive": int(pop),
                "resource_pool": float(res),
                "mean_authority": float(auth),
                "disaster_events": int(row.disaster_events or 0),
            }
        )

    first_shock_turn: int | None = None
    for e in sim.events:
        if e.action.value == "disaster":
            first_shock_turn = int(e.turn)
            break
    if first_shock_turn is None:
        for row in series:
            if row["disaster_events"] > 0:
                first_shock_turn = int(row["turn"])
                break

    initial_pop = int(sim.world.initial_population or len(sim.agents))
    initial_res = float(getattr(sim.world, "initial_resource_pool", 0.0) or 0.0)
    if initial_res <= 0 and series:
        initial_res = float(series[0]["resource_pool"])

    def _pop_before(turn: int) -> int:
        prior = [s for s in series if s["turn"] < turn]
        if prior:
            return int(prior[-1]["population_alive"])
        return initial_pop

    def _res_before(turn: int) -> float:
        prior = [s for s in series if s["turn"] < turn]
        if prior:
            return float(prior[-1]["resource_pool"])
        return initial_res

    if first_shock_turn is None:
        window = series
        pop_pre = initial_pop
        res_pre = initial_res
    else:
        window = [s for s in series if s["turn"] >= first_shock_turn] or series
        pop_pre = _pop_before(first_shock_turn)
        res_pre = _res_before(first_shock_turn)

    pops = [int(s["population_alive"]) for s in window] or [alive_now]
    pop_trough = min(pops)
    pop_end = alive_now
    drop = max(pop_pre - pop_trough, 0)
    if drop <= 0:
        pop_recovery_ratio = 1.0 if pop_end >= pop_pre else 0.0
    else:
        pop_recovery_ratio = round((pop_end - pop_trough) / drop, 3)
        pop_recovery_ratio = max(0.0, min(1.5, pop_recovery_ratio))
    pop_retention_ratio = round(pop_end / max(pop_pre, 1), 3)

    # Resource halftime: only defined if pool fell below 50% of pre-shock after the shock.
    resource_recovery_halftime: int | None = None
    resource_breached_half = False
    if first_shock_turn is not None and res_pre > 0:
        target = res_pre * 0.5
        after = [s for s in series if s["turn"] >= first_shock_turn]
        if after:
            min_after = min(float(s["resource_pool"]) for s in after)
            resource_breached_half = min_after < target
            if resource_breached_half:
                for s in after:
                    if float(s["resource_pool"]) >= target:
                        resource_recovery_halftime = int(s["turn"] - first_shock_turn)
                        break

    # Regime break: authority collapses after shock (start is often anarchy in CE).
    auth_vals = [float(s["mean_authority"]) for s in window] or [0.5]
    auth_trough = min(auth_vals)
    auth_pre = 0.5
    if first_shock_turn is not None:
        prior_auth = [s for s in series if s["turn"] < first_shock_turn]
        if prior_auth:
            auth_pre = float(prior_auth[-1]["mean_authority"])
        elif series:
            auth_pre = float(series[0]["mean_authority"])
    elif series:
        auth_pre = float(series[0]["mean_authority"])
    regime_to_anarchy = any(
        e.action.value == "regime" and "anarchy" in (e.detail or "").lower()
        for e in sim.events
        if first_shock_turn is None or e.turn >= first_shock_turn
    )
    regime_break = bool(
        auth_trough < AUTHORITY_BREAK_THRESHOLD
        or (auth_pre - auth_trough) >= 0.2
        or regime_to_anarchy
    )

    post_events = [
        e
        for e in sim.events
        if first_shock_turn is None or e.turn >= first_shock_turn
    ]
    post_coop = sum(1 for e in post_events if e.action.value == "cooperate")
    post_conflict = sum(1 for e in post_events if e.action.value == "conflict")
    denom = post_coop + post_conflict
    coop_vs_conflict_post_shock = round(post_coop / denom, 3) if denom else None

    # Label: prefer bounce-back when present; else use retention under chronic decline.
    bounced = pop_end > pop_trough * 1.02 and drop > 0
    if bounced and pop_recovery_ratio >= 0.6 and not regime_break:
        resilience_label = "recovered"
    elif pop_retention_ratio >= 0.55 and not regime_break:
        resilience_label = "recovered"
    elif pop_retention_ratio < 0.35 or (pop_recovery_ratio < 0.15 and pop_retention_ratio < 0.45):
        resilience_label = "collapsed"
    else:
        resilience_label = "stressed"

    return {
        "shock_count": shock_count,
        "disaster_deaths": disaster_deaths,
        "first_shock_turn": first_shock_turn,
        "pop_pre_shock": pop_pre,
        "pop_trough": pop_trough,
        "pop_end": pop_end,
        "pop_recovery_ratio": pop_recovery_ratio,
        "pop_retention_ratio": pop_retention_ratio,
        "resource_pre_shock": round(res_pre, 1),
        "resource_end": round(resource_now, 1),
        "resource_breached_half": resource_breached_half,
        "resource_recovery_halftime": resource_recovery_halftime,
        "authority_trough": round(auth_trough, 3),
        "regime_break": regime_break,
        "coop_vs_conflict_post_shock": coop_vs_conflict_post_shock,
        "resilience_label": resilience_label,
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
    resilience = compute_resilience_metrics(sim)

    protocol = sim.experiment_protocol
    if not protocol and sim.experiment_variant:
        try:
            protocol = protocol_for_variant(sim.experiment_variant)
        except ValueError:
            protocol = None

    return {
        "variant": sim.experiment_variant,
        "variant_label_ja": variant_label_ja(sim.experiment_variant or ""),
        "protocol": protocol,
        "shock_pulse_turns": list(sim.shock_pulse_turns or []),
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
        # Phase B resilience (flat keys for analysis tables)
        "shock_count": resilience["shock_count"],
        "disaster_deaths": resilience["disaster_deaths"],
        "first_shock_turn": resilience["first_shock_turn"],
        "pop_trough": resilience["pop_trough"],
        "pop_recovery_ratio": resilience["pop_recovery_ratio"],
        "pop_retention_ratio": resilience["pop_retention_ratio"],
        "resource_recovery_halftime": resilience["resource_recovery_halftime"],
        "regime_break": resilience["regime_break"],
        "coop_vs_conflict_post_shock": resilience["coop_vs_conflict_post_shock"],
        "resilience_label": resilience["resilience_label"],
        "resilience": resilience,
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
