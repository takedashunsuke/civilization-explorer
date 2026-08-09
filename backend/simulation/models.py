from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class InstitutionType(str, Enum):
    anarchy = "anarchy"
    autocracy = "autocracy"
    democracy = "democracy"


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


class WorldParams(BaseModel):
    seed: int = 42
    population: int = Field(default=8, ge=2, le=20)
    resource_pool: float = 100.0
    education_level: float = Field(default=0.5, ge=0, le=1)
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    institution: InstitutionType = InstitutionType.democracy
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


class InstitutionState(BaseModel):
    authority: float = Field(default=0.5, ge=0, le=1)
    treasury: float = 0.0


class WorldState(BaseModel):
    turn: int = 0
    seed: int
    population_cap: int
    resource_pool: float
    education_level: float
    tax_rate: float
    institution: InstitutionType
    initial_values: InitialValues
    institution_runtime: InstitutionState = Field(default_factory=InstitutionState)


class EventRecord(BaseModel):
    turn: int
    actor_id: str
    action: ActionType
    target_id: str | None = None
    success: bool | None = None
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
