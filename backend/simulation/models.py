from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class InstitutionType(str, Enum):
    anarchy = "anarchy"
    autocracy = "autocracy"
    democracy = "democracy"


class GeographyType(str, Enum):
    africa = "africa"
    asia = "asia"
    europe = "europe"
    america = "america"
    oceania = "oceania"
    middle_east = "middle_east"
    world = "world"
    # legacy values still accepted by the API
    island = "island"
    continent = "continent"


class LandformType(str, Enum):
    continent = "continent"
    island = "island"


class ClimateType(str, Enum):
    temperate = "temperate"
    cold = "cold"
    wetland = "wetland"
    arid = "arid"


class ReligionType(str, Enum):
    folk = "folk"
    polytheism = "polytheism"
    monotheism = "monotheism"
    secular = "secular"
    organized = "organized"  # legacy: treated as monotheism


YEARS_PER_TURN = 10
MAX_CALENDAR_YEAR = 2500


def resolve_theater_and_landform(
    geography: GeographyType,
    landform: LandformType,
) -> tuple[GeographyType, LandformType]:
    if geography == GeographyType.island:
        return GeographyType.asia, LandformType.island
    if geography == GeographyType.continent:
        return GeographyType.europe, LandformType.continent
    return geography, landform


class TerrainState(BaseModel):
    cols: int = 48
    rows: int = 48
    biomes: list[str] = Field(default_factory=list)


class Allegiance(str, Enum):
    obey = "obey"
    resist = "resist"
    neutral = "neutral"


class ActionType(str, Enum):
    wait = "wait"
    cooperate = "cooperate"
    conflict = "conflict"
    migrate = "migrate"
    obey = "obey"
    resist = "resist"
    birth = "birth"
    death = "death"
    lead = "lead"
    trait = "trait"
    disaster = "disaster"
    regime = "regime"
    observe = "observe"


class Position(BaseModel):
    x: float
    y: float


class Personality(BaseModel):
    cooperation: float = Field(ge=0, le=1, default=0.5)
    aggression: float = Field(ge=0, le=1, default=0.5)
    ambition: float = Field(ge=0, le=1, default=0.5)


class InitialValues(BaseModel):
    cooperation: float = Field(ge=0, le=1, default=0.5)
    authority_acceptance: float = Field(ge=0, le=1, default=0.5)
    ambition: float = Field(ge=0, le=1, default=0.5)
    inequality: float = Field(ge=0, le=1, default=0.5)


class RegionParams(BaseModel):
    id: GeographyType
    subregion_id: str | None = None
    population: int = Field(default=1000, ge=1000, le=10000)
    institution: InstitutionType = InstitutionType.democracy
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    education_level: float = Field(default=0.5, ge=0, le=1)
    religion: ReligionType = ReligionType.folk
    trade_openness: float = Field(default=0.5, ge=0, le=1)
    initial_values: InitialValues = Field(default_factory=InitialValues)
    trait_rate: float = Field(default=0.1, ge=0, le=1)
    welfare_rate: float = Field(default=0.0, ge=0, le=1)
    resource_pool: float | None = None
    disaster_frequency: float | None = Field(default=None, ge=0, le=1)


class WorldParams(BaseModel):
    seed: int = 42
    population: int = Field(default=1000, ge=1000, le=10000)
    resource_pool: float = 100.0
    education_level: float = Field(default=0.5, ge=0, le=1)
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    institution: InstitutionType = InstitutionType.democracy
    # Astronomical year: AD 1 = 1, BC 1 = 0, BC 44 = -43
    start_year: int = Field(default=1000, ge=-50000, le=2500)
    geography: GeographyType = GeographyType.world
    landform: LandformType = LandformType.continent
    climate: ClimateType = ClimateType.temperate
    disaster_frequency: float = Field(default=0.2, ge=0, le=1)
    religion: ReligionType = ReligionType.folk
    initial_values: InitialValues = Field(default_factory=InitialValues)
    regions: list[RegionParams] = Field(default_factory=list)


class AgentState(BaseModel):
    id: str
    name: str
    position: Position
    wealth: float
    energy: float = Field(ge=0, le=1)
    happiness: float = Field(ge=0, le=1)
    personality: Personality
    goal: str = "survive"
    memory: list[str] = Field(default_factory=list)
    settlement_id: str | None = None
    allegiance: Allegiance = Allegiance.neutral
    alive: bool = True
    traits: list[str] = Field(default_factory=list)
    age: int = 20
    region_id: str | None = None
    subregion_id: str | None = None
    # Recent disaster / shock pressure (0–1). Raises mortality until it decays.
    shock_stress: float = Field(default=0.0, ge=0, le=1)


class RelationshipState(BaseModel):
    a_id: str
    b_id: str
    trust: float = Field(default=0.0, ge=-1, le=1)
    affinity: float = Field(default=0.0, ge=-1, le=1)


class SettlementState(BaseModel):
    id: str
    position: Position
    member_ids: list[str] = Field(default_factory=list)
    shared_wealth: float = 0.0
    leader_id: str | None = None
    region_id: str | None = None
    subregion_id: str | None = None


class InstitutionState(BaseModel):
    authority: float = Field(default=0.5, ge=0, le=1)
    treasury: float = 0.0


class RegionState(BaseModel):
    id: GeographyType
    subregion_id: str | None = None
    landform: LandformType = LandformType.continent
    climate: ClimateType = ClimateType.temperate
    disaster_frequency: float = Field(default=0.2, ge=0, le=1)
    sanitation: float = Field(default=0.5, ge=0, le=1)
    resource_pool: float = 100.0
    education_level: float = 0.5
    tax_rate: float = 0.1
    institution: InstitutionType = InstitutionType.democracy
    religion: ReligionType = ReligionType.folk
    trade_openness: float = Field(default=0.5, ge=0, le=1)
    initial_values: InitialValues = Field(default_factory=InitialValues)
    terrain: TerrainState = Field(default_factory=TerrainState)
    institution_runtime: InstitutionState = Field(default_factory=InstitutionState)
    trait_rate: float = Field(default=0.1, ge=0, le=1)
    welfare_rate: float = Field(default=0.0, ge=0, le=1)


class WorldState(BaseModel):
    turn: int = 0
    years_per_turn: int = YEARS_PER_TURN
    seed: int
    initial_population: int = 8
    initial_total_wealth: float = 0.0
    initial_resource_pool: float = 0.0
    population_cap: int
    resource_pool: float
    education_level: float
    tax_rate: float
    institution: InstitutionType
    start_year: int = 1000
    geography: GeographyType = GeographyType.world
    landform: LandformType = LandformType.continent
    climate: ClimateType = ClimateType.temperate
    disaster_frequency: float = Field(default=0.2, ge=0, le=1)
    religion: ReligionType = ReligionType.folk
    terrain: TerrainState = Field(default_factory=TerrainState)
    initial_values: InitialValues
    institution_runtime: InstitutionState = Field(default_factory=InstitutionState)
    regions: list[RegionState] = Field(default_factory=list)
    fired_shock_ids: list[str] = Field(default_factory=list)


class EventRecord(BaseModel):
    turn: int
    actor_id: str
    action: ActionType
    target_id: str | None = None
    success: bool | None = None
    detail_key: str = "wait"
    detail: str
    deltas: dict[str, float] = Field(default_factory=dict)
    lon: float | None = None
    lat: float | None = None
    alert: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class RegionMetricsSnapshot(BaseModel):
    region_id: str
    subregion_id: str | None = None
    inequality: float
    mean_trust: float
    cooperation_rate: float
    authority: float
    mean_happiness: float
    # Semantic overlay (LLM when wired; heuristic fallback otherwise)
    tension: float = 0.0
    prosperity: float = 0.0
    discontent: float = 0.0
    cohesion: float = 0.0
    rising_archetype: str = "none"
    trajectory: str = "stagnation"
    summary: str = ""
    reading_source: str = "heuristic"


class MetricsSnapshot(BaseModel):
    inequality: float
    mean_trust: float
    cooperation_rate: float
    authority: float
    mean_happiness: float
    regions: list[RegionMetricsSnapshot] = Field(default_factory=list)
    world_summary: str = ""
    reading_source: str = "heuristic"


class RegionReading(BaseModel):
    region_id: str
    subregion_id: str | None = None
    tension: float = Field(default=0.0, ge=0, le=1)
    prosperity: float = Field(default=0.0, ge=0, le=1)
    discontent: float = Field(default=0.0, ge=0, le=1)
    cohesion: float = Field(default=0.0, ge=0, le=1)
    rising_archetype: str = "none"
    trajectory: str = "stagnation"
    summary: str = ""
    source: Literal["llm", "heuristic"] = "heuristic"


class RegionPolicy(BaseModel):
    """Institution / polity stance for the turn (not per-person decisions)."""

    region_id: str
    subregion_id: str | None = None
    action: ActionType = ActionType.wait
    intensity: float = Field(default=0.3, ge=0, le=1)
    reason: str = ""
    source: Literal["llm", "heuristic"] = "heuristic"


class HistoryRecord(BaseModel):
    turn: int
    summary: str
    metrics: MetricsSnapshot
    # Phase B resilience series (optional for older payloads)
    population_alive: int | None = None
    resource_pool: float | None = None
    mean_authority: float | None = None
    disaster_events: int = 0


class PlannedShock(BaseModel):
    """Pre-generated crisis cell: identical across resilience variants."""

    turn: int
    region_id: str
    subregion_id: str | None = None
    kind: str
    intensity: float = 1.0


class ChosenAction(BaseModel):
    agent_id: str
    action: ActionType
    target_id: str | None = None
    reason: str = ""
    source: Literal["llm", "heuristic"] = "heuristic"
    rationale: str = ""


class SimulationState(BaseModel):
    id: str
    status: Literal["created", "running", "paused"] = "created"
    controlled_experiment: bool = False
    experiment_variant: str | None = None
    experiment_seed: int | None = None
    # environment = resource/disaster knobs; resilience = same shock × social structure
    experiment_protocol: str | None = None
    # Forced crisis turns (identical across resilience variants)
    shock_pulse_turns: list[int] = Field(default_factory=list)
    # Pre-generated shock column (resilience protocol). Empty = stochastic path.
    shock_plan: list[PlannedShock] = Field(default_factory=list)
    world: WorldState
    agents: list[AgentState]
    relationships: list[RelationshipState]
    settlements: list[SettlementState]
    events: list[EventRecord] = Field(default_factory=list)
    history: list[HistoryRecord] = Field(default_factory=list)
    last_metrics: MetricsSnapshot | None = None
    region_readings: list[RegionReading] = Field(default_factory=list)
    region_policies: list[RegionPolicy] = Field(default_factory=list)
    world_summary: str = ""


WorldParams = WorldParams
resolve_theater_and_landform = resolve_theater_and_landform
