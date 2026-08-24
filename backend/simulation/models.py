from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class InstitutionType(str, Enum):
    anarchy = "anarchy"
    autocracy = "autocracy"
    democracy = "democracy"


class GeographyType(str, Enum):
    asia = "asia"
    europe = "europe"
    middle_east = "middle_east"
    america = "america"
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
    inequality: float = Field(ge=0, le=1, default=0.35)


class WorldParams(BaseModel):
    seed: int = 42
    population: int = Field(default=8, ge=2, le=100)
    resource_pool: float = 100.0
    education_level: float = Field(default=0.5, ge=0, le=1)
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    institution: InstitutionType = InstitutionType.democracy
    # Astronomical year: AD 1 = 1, BC 1 = 0, BC 44 = -43
    start_year: int = Field(default=700, ge=-50000, le=3000)
    geography: GeographyType = GeographyType.asia
    landform: LandformType = LandformType.continent
    climate: ClimateType = ClimateType.temperate
    initial_values: InitialValues = Field(default_factory=InitialValues)


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


class InstitutionState(BaseModel):
    authority: float = Field(default=0.5, ge=0, le=1)
    treasury: float = 0.0


class WorldState(BaseModel):
    turn: int = 0
    seed: int
    initial_population: int = 8
    initial_total_wealth: float = 0.0
    population_cap: int
    resource_pool: float
    education_level: float
    tax_rate: float
    institution: InstitutionType
    start_year: int = 700
    geography: GeographyType = GeographyType.asia
    landform: LandformType = LandformType.continent
    climate: ClimateType = ClimateType.temperate
    terrain: TerrainState = Field(default_factory=TerrainState)
    initial_values: InitialValues
    institution_runtime: InstitutionState = Field(default_factory=InstitutionState)


class EventRecord(BaseModel):
    turn: int
    actor_id: str
    action: ActionType
    target_id: str | None = None
    success: bool | None = None
    detail_key: str = "wait"
    detail: str
    deltas: dict[str, float] = Field(default_factory=dict)


class MetricsSnapshot(BaseModel):
    inequality: float
    mean_trust: float
    cooperation_rate: float
    authority: float
    mean_happiness: float


class HistoryRecord(BaseModel):
    turn: int
    summary: str
    metrics: MetricsSnapshot


class ChosenAction(BaseModel):
    agent_id: str
    action: ActionType
    target_id: str | None = None
    reason: str = ""


class SimulationState(BaseModel):
    id: str
    status: Literal["created", "running", "paused"] = "created"
    world: WorldState
    agents: list[AgentState]
    relationships: list[RelationshipState]
    settlements: list[SettlementState]
    events: list[EventRecord] = Field(default_factory=list)
    history: list[HistoryRecord] = Field(default_factory=list)
    last_metrics: MetricsSnapshot | None = None


WorldParams = WorldParams
resolve_theater_and_landform = resolve_theater_and_landform
