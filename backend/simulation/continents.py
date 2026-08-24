from __future__ import annotations

from simulation.models import ClimateType, GeographyType, LandformType

CONTINENT_IDS: tuple[GeographyType, ...] = (
    GeographyType.africa,
    GeographyType.europe,
    GeographyType.asia,
    GeographyType.america,
    GeographyType.oceania,
)

# 地理・自然・食は実験者がいじらず、比較の背景として固定する。
CONTINENT_PRESETS: dict[GeographyType, dict[str, object]] = {
    GeographyType.africa: {
        "landform": LandformType.continent,
        "climate": ClimateType.arid,
        "resource_pool": 72.0,
        "disaster_frequency": 0.32,
    },
    GeographyType.europe: {
        "landform": LandformType.continent,
        "climate": ClimateType.temperate,
        "resource_pool": 118.0,
        "disaster_frequency": 0.14,
    },
    GeographyType.asia: {
        "landform": LandformType.continent,
        "climate": ClimateType.wetland,
        "resource_pool": 108.0,
        "disaster_frequency": 0.28,
    },
    GeographyType.america: {
        "landform": LandformType.continent,
        "climate": ClimateType.temperate,
        "resource_pool": 124.0,
        "disaster_frequency": 0.2,
    },
    GeographyType.oceania: {
        "landform": LandformType.island,
        "climate": ClimateType.wetland,
        "resource_pool": 78.0,
        "disaster_frequency": 0.38,
    },
}
