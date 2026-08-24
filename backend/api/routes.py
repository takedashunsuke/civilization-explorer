from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from simulation import create_simulation, tick
from simulation.llm import describe_provider
from simulation.continents import resolve_subregion
from simulation.models import (
    ClimateType,
    GeographyType,
    InitialValues,
    InstitutionType,
    LandformType,
    RegionParams,
    ReligionType,
    SimulationState,
    WorldParams,
)

router = APIRouter()

_STORE: dict[str, SimulationState] = {}


class RegionCreateBody(BaseModel):
    id: str
    subregion: str | None = None
    population: int = Field(default=4, ge=2, le=40)
    institution: str = "democracy"
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    education_level: float = Field(default=0.5, ge=0, le=1)
    religion: str = "folk"
    initial_values: dict[str, float] | None = None


class CreateSimulationRequest(BaseModel):
    seed: int | None = None
    population: int = Field(default=8, ge=2, le=100)
    resource_pool: float = 100.0
    education_level: float = Field(default=0.5, ge=0, le=1)
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    institution: str = "democracy"
    start_year: int = Field(default=700, ge=-50000, le=3000)
    geography: str = "world"
    landform: str = "continent"
    climate: str = "temperate"
    disaster_frequency: float = Field(default=0.2, ge=0, le=1)
    religion: str = "folk"
    initial_values: dict[str, float] | None = None
    regions: list[RegionCreateBody] | None = None


class TickRequest(BaseModel):
    n: int = Field(default=1, ge=1, le=50)


def _to_public(sim: SimulationState) -> dict[str, Any]:
    return sim.model_dump()


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "llm": describe_provider()}


@router.post("/simulations")
def create_sim(body: CreateSimulationRequest) -> dict[str, Any]:
    try:
        institution = InstitutionType(body.institution)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid institution: {body.institution}") from exc
    try:
        geography = GeographyType(body.geography)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid geography: {body.geography}") from exc
    try:
        landform = LandformType(body.landform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid landform: {body.landform}") from exc
    try:
        climate = ClimateType(body.climate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid climate: {body.climate}") from exc
    try:
        religion = ReligionType(body.religion)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid religion: {body.religion}") from exc

    initial = InitialValues()
    if body.initial_values:
        initial = InitialValues(
            cooperation=body.initial_values.get("cooperation", initial.cooperation),
            authority_acceptance=body.initial_values.get(
                "authority_acceptance", initial.authority_acceptance
            ),
            ambition=body.initial_values.get("ambition", initial.ambition),
            inequality=body.initial_values.get("inequality", initial.inequality),
        )

    region_models: list[RegionParams] = []
    for item in body.regions or []:
        try:
            rid = GeographyType(item.id)
            r_inst = InstitutionType(item.institution)
            r_rel = ReligionType(item.religion)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid region: {item.id}") from exc
        r_init = InitialValues()
        if item.initial_values:
            r_init = InitialValues(
                cooperation=item.initial_values.get("cooperation", r_init.cooperation),
                authority_acceptance=item.initial_values.get(
                    "authority_acceptance", r_init.authority_acceptance
                ),
                ambition=item.initial_values.get("ambition", r_init.ambition),
                inequality=item.initial_values.get("inequality", r_init.inequality),
            )
        region_models.append(
            RegionParams(
                id=rid,
                subregion_id=resolve_subregion(rid, item.subregion),
                population=item.population,
                institution=r_inst,
                tax_rate=item.tax_rate,
                education_level=item.education_level,
                religion=r_rel,
                initial_values=r_init,
            )
        )

    params = WorldParams(
        seed=body.seed if body.seed is not None else uuid.uuid4().int % 1_000_000_000,
        population=body.population,
        resource_pool=body.resource_pool,
        education_level=body.education_level,
        tax_rate=body.tax_rate,
        institution=institution,
        start_year=body.start_year,
        geography=geography,
        landform=landform,
        climate=climate,
        disaster_frequency=body.disaster_frequency,
        religion=religion,
        initial_values=initial,
        regions=region_models,
    )
    sim_id = str(uuid.uuid4())
    sim = create_simulation(sim_id, params)
    _STORE[sim_id] = sim
    return _to_public(sim)


@router.get("/simulations")
def list_sims() -> list[dict[str, Any]]:
    return [
        {
            "id": s.id,
            "status": s.status,
            "turn": s.world.turn,
            "seed": s.world.seed,
            "population": len(s.agents),
            "last_metrics": s.last_metrics.model_dump() if s.last_metrics else None,
        }
        for s in _STORE.values()
    ]


@router.get("/simulations/{sim_id}")
def get_sim(sim_id: str) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    return _to_public(sim)


@router.post("/simulations/{sim_id}/start")
def start_sim(sim_id: str) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    sim.status = "running"
    return _to_public(sim)


@router.post("/simulations/{sim_id}/pause")
def pause_sim(sim_id: str) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    sim.status = "paused"
    return _to_public(sim)


@router.post("/simulations/{sim_id}/tick")
def tick_sim(sim_id: str, body: TickRequest | None = None) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    if sim.status == "created":
        sim.status = "running"
    n = body.n if body else 1
    tick(sim, n=n)
    return _to_public(sim)


@router.get("/simulations/{sim_id}/events")
def get_events(sim_id: str, limit: int = 100) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    events = sim.events[-limit:]
    return {
        "id": sim.id,
        "turn": sim.world.turn,
        "events": [e.model_dump() for e in events],
        "history": [h.model_dump() for h in sim.history[-limit:]],
    }


@router.get("/simulations/{sim_id}/replay")
def get_replay(sim_id: str) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    return {
        "id": sim.id,
        "seed": sim.world.seed,
        "population": sim.world.population_cap,
        "resource_pool": sim.world.resource_pool,
        "education_level": sim.world.education_level,
        "tax_rate": sim.world.tax_rate,
        "institution": sim.world.institution.value,
        "start_year": sim.world.start_year,
        "geography": sim.world.geography.value,
        "landform": sim.world.landform.value,
        "climate": sim.world.climate.value,
        "initial_values": sim.world.initial_values.model_dump(),
    }
