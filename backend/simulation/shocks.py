from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from simulation.continents import SUBREGION_CENTERS
from simulation.models import ActionType, ClimateType, EventRecord, LandformType, RegionState, SimulationState

_DATA = Path(__file__).resolve().parent / "data" / "historic_earthquakes.json"


@lru_cache(maxsize=1)
def historic_earthquakes() -> list[dict[str, Any]]:
    payload = json.loads(_DATA.read_text(encoding="utf-8"))
    return list(payload.get("events") or [])


def calendar_year(sim: SimulationState) -> int:
    years = max(1, int(getattr(sim.world, "years_per_turn", 10)))
    return int(sim.world.start_year) + int(sim.world.turn) * years


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _region_for_sub(sim: SimulationState, subregion: str) -> RegionState | None:
    for region in sim.world.regions:
        if region.subregion_id == subregion:
            return region
    return None


def _hit_agents(sim: SimulationState, region: RegionState):
    sid = region.subregion_id
    if sid:
        return [a for a in sim.agents if a.alive and a.subregion_id == sid]
    return [a for a in sim.agents if a.alive and a.region_id == region.id.value]


def _apply_quake_damage(agents: list, magnitude: float) -> float:
    loss = 0.0
    scale = 1.2 if magnitude < 8.5 else 2.2 if magnitude < 9.0 else 3.2
    for agent in agents:
        agent.wealth = max(0.0, agent.wealth - scale)
        agent.happiness = clamp(agent.happiness - 0.04 * scale)
        agent.energy = clamp(agent.energy - 0.05 * scale)
        loss += scale
    return loss


def apply_historic_quakes(sim: SimulationState) -> list[EventRecord]:
    year = calendar_year(sim)
    fired = set(sim.world.fired_shock_ids)
    out: list[EventRecord] = []
    for item in historic_earthquakes():
        if item["id"] in fired:
            continue
        if int(item["year"]) != year:
            continue
        region = _region_for_sub(sim, str(item["subregion"]))
        if not region:
            continue
        hit = _hit_agents(sim, region)
        if not hit:
            continue
        mag = float(item["magnitude"])
        loss = _apply_quake_damage(hit, mag)
        fired.add(item["id"])
        alert = "red" if mag >= 8.5 else "yellow"
        out.append(
            EventRecord(
                turn=sim.world.turn,
                actor_id=region.subregion_id or region.id.value,
                action=ActionType.disaster,
                detail_key="historic_quake",
                detail=item["wiki"],
                deltas={"n": float(len(hit)), "loss": loss, "magnitude": mag, "lon": float(item["lon"]), "lat": float(item["lat"])},
                lon=float(item["lon"]),
                lat=float(item["lat"]),
                alert=alert,
                extra={
                    "wiki": str(item["wiki"]),
                    "name_en": str(item["name_en"]),
                    "name_ja": str(item["name_ja"]),
                    "mag_label": str(item["magnitude_label"]),
                    "year": str(item["year"]),
                },
            )
        )
    sim.world.fired_shock_ids = list(fired)
    return out


def apply_epidemics(sim: SimulationState, rng) -> list[EventRecord]:
    out: list[EventRecord] = []
    for region in sim.world.regions:
        sanitation = getattr(region, "sanitation", 0.5)
        chance = (1.0 - sanitation) * 0.09
        chance += getattr(region, "trade_openness", 0.5) * 0.035
        if region.climate == ClimateType.wetland:
            chance += 0.03
        if rng.random() >= chance:
            continue
        hit = _hit_agents(sim, region)
        if not hit:
            continue
        if len(hit) > 2:
            hit = rng.sample(hit, max(2, len(hit) // 2))
        for agent in hit:
            agent.energy = clamp(agent.energy - 0.16)
            agent.happiness = clamp(agent.happiness - 0.08)
            if rng.random() < (1.0 - sanitation) * 0.12:
                agent.alive = False
        theater = region.subregion_id or region.id.value
        lon, lat = SUBREGION_CENTERS.get(theater, (0.0, 0.0))
        alert = "red" if sanitation < 0.4 else "yellow"
        out.append(
            EventRecord(
                turn=sim.world.turn,
                actor_id=theater,
                action=ActionType.disaster,
                detail_key="epidemic",
                detail=f"epidemic in {theater}",
                deltas={"n": float(len(hit))},
                lon=lon,
                lat=lat,
                alert=alert,
                extra={"kind": "epidemic"},
            )
        )
    return out


def apply_weather_shocks(sim: SimulationState, rng) -> list[EventRecord]:
    out: list[EventRecord] = []
    for region in sim.world.regions:
        chance = 0.04 + region.disaster_frequency * 0.12
        if rng.random() >= chance:
            continue
        if region.climate == ClimateType.arid:
            key = "weather_drought"
        elif region.climate == ClimateType.cold:
            key = "weather_blizzard"
        elif region.landform == LandformType.island or region.climate == ClimateType.wetland:
            key = "weather_storm"
        else:
            key = "weather_heat"
        hit = _hit_agents(sim, region)
        if not hit:
            continue
        for agent in hit:
            agent.energy = clamp(agent.energy - 0.07)
            agent.wealth = max(0.0, agent.wealth - 0.8)
        region.resource_pool = max(0.0, region.resource_pool - 6.0)
        theater = region.subregion_id or region.id.value
        lon, lat = SUBREGION_CENTERS.get(theater, (0.0, 0.0))
        out.append(
            EventRecord(
                turn=sim.world.turn,
                actor_id=theater,
                action=ActionType.disaster,
                detail_key=key,
                detail=key,
                deltas={"n": float(len(hit))},
                lon=lon,
                lat=lat,
                alert="yellow",
                extra={"kind": key},
            )
        )
    return out
