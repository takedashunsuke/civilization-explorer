from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from simulation.continents import SUBREGION_CENTERS
from simulation.models import (
    ActionType,
    ClimateType,
    EventRecord,
    LandformType,
    PlannedShock,
    RegionState,
    SimulationState,
)

_DATA = Path(__file__).resolve().parent / "data" / "historic_earthquakes.json"
MIN_ALIVE_PER_REGION = 2
RESOURCE_COMFORT = 100.0


@lru_cache(maxsize=1)
def historic_earthquakes() -> list[dict[str, Any]]:
    payload = json.loads(_DATA.read_text(encoding="utf-8"))
    return list(payload.get("events") or [])


def calendar_year(sim: SimulationState) -> int:
    years = max(1, int(getattr(sim.world, "years_per_turn", 10)))
    return int(sim.world.start_year) + int(sim.world.turn) * years


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def stable_int(*parts: object) -> int:
    """Process-independent fingerprint (do not use Python's salted hash())."""
    acc = 2166136261
    for part in parts:
        for ch in str(part):
            acc ^= ord(ch)
            acc = (acc * 16777619) % (2**32)
    return acc


def _resource_scarce_boost(pool: float) -> float:
    scarcity = max(0.0, min(1.0, 1.0 - float(pool) / RESOURCE_COMFORT))
    return 0.06 * scarcity


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
    stress = 0.2 if magnitude < 8.5 else 0.35
    for agent in agents:
        agent.wealth = max(0.0, agent.wealth - scale)
        agent.happiness = clamp(agent.happiness - 0.04 * scale)
        agent.energy = clamp(agent.energy - 0.05 * scale)
        agent.shock_stress = clamp(agent.shock_stress + stress)
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
        # Historic quakes can kill a small share (Phase A lethality pathway).
        kill_p = 0.02 + max(0.0, mag - 7.5) * 0.035
        rng = random.Random((sim.world.seed * 10007 + stable_int(item["id"])) % (2**32))
        killed = 0
        alive_n = len(hit)
        for agent in hit:
            if alive_n <= MIN_ALIVE_PER_REGION:
                break
            if rng.random() >= kill_p:
                continue
            agent.alive = False
            agent.energy = 0.0
            alive_n -= 1
            killed += 1
            out.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=agent.id,
                    action=ActionType.death,
                    success=False,
                    detail_key="death_disaster",
                    detail=f"{agent.id} died in historic quake {item['id']}",
                    deltas={"age": float(agent.age), "magnitude": mag},
                )
            )
        fired.add(item["id"])
        alert = "red" if mag >= 8.5 or killed else "yellow"
        out.append(
            EventRecord(
                turn=sim.world.turn,
                actor_id=region.subregion_id or region.id.value,
                action=ActionType.disaster,
                detail_key="historic_quake",
                detail=item["wiki"],
                deltas={
                    "n": float(len(hit)),
                    "loss": loss,
                    "magnitude": mag,
                    "lon": float(item["lon"]),
                    "lat": float(item["lat"]),
                    "killed": float(killed),
                },
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
        # Disaster-prone worlds also struggle more with disease pressure.
        chance += getattr(region, "disaster_frequency", 0.2) * 0.04
        if region.climate == ClimateType.wetland:
            chance += 0.03
        if rng.random() >= chance:
            continue
        out.extend(apply_epidemic_to_region(sim, region, rng))
    return out


def apply_epidemic_to_region(sim: SimulationState, region: RegionState, rng) -> list[EventRecord]:
    out: list[EventRecord] = []
    sanitation = getattr(region, "sanitation", 0.5)
    hit = _hit_agents(sim, region)
    if hit and len(hit) > 2:
        hit = rng.sample(hit, max(2, len(hit) // 2))
    killed = 0
    alive_n = len(_hit_agents(sim, region))
    for agent in hit:
        agent.energy = clamp(agent.energy - 0.16)
        agent.happiness = clamp(agent.happiness - 0.08)
        agent.shock_stress = clamp(agent.shock_stress + 0.16)
        kill_p = (1.0 - sanitation) * 0.12 + _resource_scarce_boost(region.resource_pool)
        if alive_n <= MIN_ALIVE_PER_REGION:
            continue
        if rng.random() < kill_p:
            agent.alive = False
            agent.energy = 0.0
            alive_n -= 1
            killed += 1
            out.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=agent.id,
                    action=ActionType.death,
                    success=False,
                    detail_key="death_disaster",
                    detail=f"{agent.id} died in epidemic",
                    deltas={"age": float(agent.age)},
                )
            )
    theater = region.subregion_id or region.id.value
    lon, lat = SUBREGION_CENTERS.get(theater, (0.0, 0.0))
    alert = "red" if sanitation < 0.4 or killed else "yellow"
    out.append(
        EventRecord(
            turn=sim.world.turn,
            actor_id=theater,
            action=ActionType.disaster,
            detail_key="epidemic",
            detail=f"epidemic in {theater}",
            deltas={"n": float(len(hit)), "killed": float(killed)},
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
        out.extend(apply_weather_to_region(sim, region, rng, weather_kind(region)))
    return out


def weather_kind(region: RegionState) -> str:
    if region.climate == ClimateType.arid:
        return "weather_drought"
    if region.climate == ClimateType.cold:
        return "weather_blizzard"
    if region.landform == LandformType.island or region.climate == ClimateType.wetland:
        return "weather_storm"
    return "weather_heat"


def apply_weather_to_region(
    sim: SimulationState,
    region: RegionState,
    rng,
    key: str,
) -> list[EventRecord]:
    out: list[EventRecord] = []
    hit = _hit_agents(sim, region)
    killed = 0
    alive_n = len(hit)
    kill_rate = 0.008 + 0.035 * region.disaster_frequency
    for agent in hit:
        agent.energy = clamp(agent.energy - 0.07)
        agent.wealth = max(0.0, agent.wealth - 0.8)
        agent.shock_stress = clamp(agent.shock_stress + 0.1 + 0.15 * region.disaster_frequency)
        if alive_n > MIN_ALIVE_PER_REGION and rng.random() < kill_rate:
            agent.alive = False
            agent.energy = 0.0
            alive_n -= 1
            killed += 1
            out.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=agent.id,
                    action=ActionType.death,
                    success=False,
                    detail_key="death_disaster",
                    detail=f"{agent.id} died in {key}",
                    deltas={"age": float(agent.age)},
                )
            )
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
            deltas={"n": float(len(hit)), "killed": float(killed)},
            lon=lon,
            lat=lat,
            alert="red" if killed else "yellow",
            extra={"kind": key},
        )
    )
    return out


PLAN_TRADE_OPENNESS = 0.5


def pick_disaster_kind(region: RegionState, rng: random.Random) -> str:
    weights: dict[str, float] = {
        "earthquake": 0.18,
        "typhoon": 0.18 if region.landform == LandformType.island else 0.08,
        "flood": 0.22 if region.climate == ClimateType.wetland else 0.1,
        "heatwave": 0.22 if region.climate == ClimateType.arid else 0.08,
        "frost": 0.22 if region.climate == ClimateType.cold else 0.06,
    }
    kinds = list(weights)
    total = sum(weights.values())
    pick = rng.random() * total
    acc = 0.0
    for kind in kinds:
        acc += weights[kind]
        if pick <= acc:
            return kind
    return kinds[-1]


def _region_ids(region: RegionState) -> tuple[str, str | None]:
    rid = region.id.value if hasattr(region.id, "value") else str(region.id)
    return rid, region.subregion_id


def ordered_regions(regions: list[RegionState]) -> list[RegionState]:
    return sorted(
        regions,
        key=lambda r: (_region_ids(r)[0], _region_ids(r)[1] or ""),
    )


def shock_plan_signature(plan: list[PlannedShock]) -> list[tuple[int, str, str]]:
    return [(s.turn, s.subregion_id or s.region_id, s.kind) for s in plan]


def generate_shock_plan(
    *,
    seed: int,
    total_turns: int,
    regions: list[RegionState],
    pulse_turns: list[int],
) -> list[PlannedShock]:
    """Build a crisis column from seed + stage + shared disaster_frequency only.

    Does not read trade_openness, institutions, or agent state, so resilience
    variants share the same (turn, region, kind) sequence.
    """
    rng = random.Random((int(seed) * 7919 + 17) % (2**32))
    ordered = ordered_regions(list(regions or []))
    pulses = {int(t) for t in pulse_turns}
    out: list[PlannedShock] = []
    n = max(0, int(total_turns))
    for turn in range(n):
        for region in ordered:
            rid, sid = _region_ids(region)
            freq = float(region.disaster_frequency)
            sanitation = float(getattr(region, "sanitation", 0.5))
            epidemic_p = (1.0 - sanitation) * 0.09
            epidemic_p += PLAN_TRADE_OPENNESS * 0.035
            epidemic_p += freq * 0.04
            if region.climate == ClimateType.wetland:
                epidemic_p += 0.03
            if rng.random() < epidemic_p:
                out.append(PlannedShock(turn=turn, region_id=rid, subregion_id=sid, kind="epidemic"))
            if rng.random() < 0.04 + freq * 0.12:
                out.append(
                    PlannedShock(
                        turn=turn,
                        region_id=rid,
                        subregion_id=sid,
                        kind=weather_kind(region),
                    )
                )
            if rng.random() < freq * 0.28:
                kind = pick_disaster_kind(region, rng)
                out.append(PlannedShock(turn=turn, region_id=rid, subregion_id=sid, kind=kind))
        if turn in pulses:
            for region in ordered:
                rid, sid = _region_ids(region)
                out.append(
                    PlannedShock(turn=turn, region_id=rid, subregion_id=sid, kind="pulse", intensity=1.0)
                )
    return out


def event_rng(seed: int, spec: PlannedShock) -> random.Random:
    return random.Random(stable_int(seed, spec.turn, spec.subregion_id or spec.region_id, spec.kind))
