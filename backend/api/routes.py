from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from simulation import apply_conditions_update, create_simulation, tick
from simulation.experiment import (
    ALL_VARIANT_IDS,
    EXPERIMENT_SEED,
    describe_experiment,
    experiment_summary,
    fresh_roster_copy,
    prepare_experiment_sim,
    world_params_for_variant,
    WORLD_VARIANT_IDS,
)
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
    population: int = Field(default=1000, ge=1000, le=10000)
    institution: str = "democracy"
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    education_level: float = Field(default=0.5, ge=0, le=1)
    religion: str = "folk"
    trade_openness: float = Field(default=0.5, ge=0, le=1)
    initial_values: dict[str, float] | None = None
    trait_rate: float = Field(default=0.1, ge=0, le=1)
    welfare_rate: float = Field(default=0.0, ge=0, le=1)


class CreateSimulationRequest(BaseModel):
    seed: int | None = None
    population: int = Field(default=1000, ge=1000, le=10000)
    resource_pool: float = 100.0
    education_level: float = Field(default=0.5, ge=0, le=1)
    tax_rate: float = Field(default=0.1, ge=0, le=1)
    institution: str = "democracy"
    start_year: int = Field(default=1000, ge=-50000, le=2500)
    geography: str = "world"
    landform: str = "continent"
    climate: str = "temperate"
    disaster_frequency: float = Field(default=0.2, ge=0, le=1)
    religion: str = "folk"
    initial_values: dict[str, float] | None = None
    regions: list[RegionCreateBody] | None = None
    controlled_experiment: bool = False
    experiment_variant: str | None = None
    experiment_seed: int | None = None


class TickRequest(BaseModel):
    n: int = Field(default=1, ge=1, le=50)


class RegionConditionsPatch(BaseModel):
    id: str
    institution: str | None = None
    tax_rate: float | None = Field(default=None, ge=0, le=1)
    education_level: float | None = Field(default=None, ge=0, le=1)
    religion: str | None = None
    trade_openness: float | None = Field(default=None, ge=0, le=1)
    welfare_rate: float | None = Field(default=None, ge=0, le=1)
    trait_rate: float | None = Field(default=None, ge=0, le=1)


class UpdateConditionsRequest(BaseModel):
    regions: list[RegionConditionsPatch] | None = None
    experiment_variant: str | None = None


def _to_public(sim: SimulationState) -> dict[str, Any]:
    return sim.model_dump()


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "llm": describe_provider()}


@router.get("/experiments/design")
def experiment_design() -> dict[str, Any]:
    return describe_experiment()


@router.post("/simulations")
def create_sim(body: CreateSimulationRequest) -> dict[str, Any]:
    if body.controlled_experiment:
        variant = (body.experiment_variant or "balanced").strip().lower()
        if variant not in ALL_VARIANT_IDS:
            raise HTTPException(status_code=400, detail=f"invalid experiment_variant: {variant}")
        seed = body.experiment_seed if body.experiment_seed is not None else EXPERIMENT_SEED
        params = world_params_for_variant(variant, seed, body.start_year)
        roster = fresh_roster_copy(seed)
        sim_id = str(uuid.uuid4())
        sim = create_simulation(sim_id, params, agent_roster=roster)
        # Default pulse schedule assumes a 20-turn (200y) demo horizon; CLI overrides via prepare.
        prepare_experiment_sim(sim, variant=variant, seed=seed, total_turns=20)
        _STORE[sim_id] = sim
        payload = _to_public(sim)
        payload["experiment_summary"] = experiment_summary(sim)
        return payload

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
                trade_openness=item.trade_openness,
                initial_values=r_init,
                trait_rate=item.trait_rate,
                welfare_rate=item.welfare_rate,
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


@router.patch("/simulations/{sim_id}/conditions")
def update_conditions(sim_id: str, body: UpdateConditionsRequest) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    if sim.world.turn <= 0 and not body.regions and not body.experiment_variant:
        raise HTTPException(status_code=400, detail="nothing to update")

    region_payload: list[dict[str, object]] | None = None
    if body.regions:
        region_payload = []
        for item in body.regions:
            patch: dict[str, object] = {"id": item.id}
            if item.institution is not None:
                try:
                    InstitutionType(item.institution)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=400, detail=f"invalid institution: {item.institution}"
                    ) from exc
                patch["institution"] = item.institution
            if item.religion is not None:
                try:
                    ReligionType(item.religion)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=f"invalid religion: {item.religion}") from exc
                patch["religion"] = item.religion
            for field in (
                "tax_rate",
                "education_level",
                "trade_openness",
                "welfare_rate",
                "trait_rate",
            ):
                value = getattr(item, field)
                if value is not None:
                    patch[field] = value
            region_payload.append(patch)

    variant = body.experiment_variant
    if variant is not None:
        variant = variant.strip().lower()
        if variant not in WORLD_VARIANT_IDS:
            raise HTTPException(
                status_code=400,
                detail="hot-swap experiment_variant is only supported for environment protocol "
                f"({', '.join(WORLD_VARIANT_IDS)})",
            )
        if not sim.controlled_experiment:
            raise HTTPException(status_code=400, detail="not a controlled experiment simulation")

    try:
        apply_conditions_update(
            sim,
            regions=region_payload,
            experiment_variant=variant,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = _to_public(sim)
    if sim.controlled_experiment:
        payload["experiment_summary"] = experiment_summary(sim)
    return payload


@router.post("/simulations/{sim_id}/tick")
def tick_sim(sim_id: str, body: TickRequest | None = None) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    if sim.status == "created":
        sim.status = "running"
    n = body.n if body else 1
    tick(sim, n=n)
    payload = _to_public(sim)
    if sim.controlled_experiment:
        payload["experiment_summary"] = experiment_summary(sim)
    return payload


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


@router.get("/simulations/{sim_id}/experiment-summary")
def get_experiment_summary(sim_id: str) -> dict[str, Any]:
    sim = _STORE.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="simulation not found")
    if not sim.controlled_experiment:
        raise HTTPException(status_code=400, detail="not a controlled experiment simulation")
    return experiment_summary(sim)


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
