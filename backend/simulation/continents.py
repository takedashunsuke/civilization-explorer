from __future__ import annotations

from simulation.models import ClimateType, GeographyType, LandformType

CONTINENT_IDS: tuple[GeographyType, ...] = (
    GeographyType.africa,
    GeographyType.europe,
    GeographyType.asia,
    GeographyType.america,
    GeographyType.oceania,
)

# UN M49 マクロ5 × サブ22。実験の列はマクロ固定、各列でサブを1つ選ぶ。
SUBREGIONS_BY_MACRO: dict[GeographyType, tuple[str, ...]] = {
    GeographyType.africa: (
        "northern_africa",
        "eastern_africa",
        "middle_africa",
        "western_africa",
        "southern_africa",
    ),
    GeographyType.asia: (
        "eastern_asia",
        "south_eastern_asia",
        "southern_asia",
        "central_asia",
        "western_asia",
    ),
    GeographyType.europe: (
        "western_europe",
        "eastern_europe",
        "northern_europe",
        "southern_europe",
    ),
    GeographyType.america: (
        "northern_america",
        "central_america",
        "caribbean",
        "south_america",
    ),
    GeographyType.oceania: (
        "australasia",
        "melanesia",
        "micronesia",
        "polynesia",
    ),
}

DEFAULT_SUBREGION: dict[GeographyType, str] = {
    GeographyType.africa: "western_africa",
    GeographyType.europe: "western_europe",
    GeographyType.asia: "eastern_asia",
    GeographyType.america: "northern_america",
    GeographyType.oceania: "australasia",
}

SUBREGION_MACRO: dict[str, GeographyType] = {
    sid: macro for macro, ids in SUBREGIONS_BY_MACRO.items() for sid in ids
}

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


def resolve_subregion(macro: GeographyType, subregion: str | None) -> str:
    allowed = SUBREGIONS_BY_MACRO.get(macro, ())
    if subregion and subregion in allowed:
        return subregion
    return DEFAULT_SUBREGION.get(macro, "eastern_asia")


# 気候・食資源・災害は実験者がいじらず、選んだサブ地域の背景として固定する。
SUBREGION_PRESETS: dict[str, dict[str, object]] = {
    "northern_africa": {
        "landform": LandformType.continent,
        "climate": ClimateType.arid,
        "resource_pool": 70.0,
        "disaster_frequency": 0.28,
    },
    "eastern_africa": {
        "landform": LandformType.continent,
        "climate": ClimateType.arid,
        "resource_pool": 78.0,
        "disaster_frequency": 0.26,
    },
    "middle_africa": {
        "landform": LandformType.continent,
        "climate": ClimateType.wetland,
        "resource_pool": 88.0,
        "disaster_frequency": 0.3,
    },
    "western_africa": {
        "landform": LandformType.continent,
        "climate": ClimateType.wetland,
        "resource_pool": 82.0,
        "disaster_frequency": 0.32,
    },
    "southern_africa": {
        "landform": LandformType.continent,
        "climate": ClimateType.temperate,
        "resource_pool": 90.0,
        "disaster_frequency": 0.22,
    },
    "eastern_asia": {
        "landform": LandformType.continent,
        "climate": ClimateType.temperate,
        "resource_pool": 112.0,
        "disaster_frequency": 0.24,
    },
    "south_eastern_asia": {
        "landform": LandformType.island,
        "climate": ClimateType.wetland,
        "resource_pool": 100.0,
        "disaster_frequency": 0.36,
    },
    "southern_asia": {
        "landform": LandformType.continent,
        "climate": ClimateType.wetland,
        "resource_pool": 104.0,
        "disaster_frequency": 0.3,
    },
    "central_asia": {
        "landform": LandformType.continent,
        "climate": ClimateType.arid,
        "resource_pool": 68.0,
        "disaster_frequency": 0.22,
    },
    "western_asia": {
        "landform": LandformType.continent,
        "climate": ClimateType.arid,
        "resource_pool": 76.0,
        "disaster_frequency": 0.26,
    },
    "western_europe": {
        "landform": LandformType.continent,
        "climate": ClimateType.temperate,
        "resource_pool": 120.0,
        "disaster_frequency": 0.14,
    },
    "eastern_europe": {
        "landform": LandformType.continent,
        "climate": ClimateType.cold,
        "resource_pool": 110.0,
        "disaster_frequency": 0.16,
    },
    "northern_europe": {
        "landform": LandformType.continent,
        "climate": ClimateType.cold,
        "resource_pool": 98.0,
        "disaster_frequency": 0.18,
    },
    "southern_europe": {
        "landform": LandformType.continent,
        "climate": ClimateType.temperate,
        "resource_pool": 108.0,
        "disaster_frequency": 0.16,
    },
    "northern_america": {
        "landform": LandformType.continent,
        "climate": ClimateType.temperate,
        "resource_pool": 126.0,
        "disaster_frequency": 0.18,
    },
    "central_america": {
        "landform": LandformType.continent,
        "climate": ClimateType.wetland,
        "resource_pool": 92.0,
        "disaster_frequency": 0.34,
    },
    "caribbean": {
        "landform": LandformType.island,
        "climate": ClimateType.wetland,
        "resource_pool": 74.0,
        "disaster_frequency": 0.42,
    },
    "south_america": {
        "landform": LandformType.continent,
        "climate": ClimateType.wetland,
        "resource_pool": 118.0,
        "disaster_frequency": 0.26,
    },
    "australasia": {
        "landform": LandformType.continent,
        "climate": ClimateType.arid,
        "resource_pool": 86.0,
        "disaster_frequency": 0.28,
    },
    "melanesia": {
        "landform": LandformType.island,
        "climate": ClimateType.wetland,
        "resource_pool": 80.0,
        "disaster_frequency": 0.36,
    },
    "micronesia": {
        "landform": LandformType.island,
        "climate": ClimateType.wetland,
        "resource_pool": 58.0,
        "disaster_frequency": 0.4,
    },
    "polynesia": {
        "landform": LandformType.island,
        "climate": ClimateType.wetland,
        "resource_pool": 62.0,
        "disaster_frequency": 0.38,
    },
}


SANITATION: dict[str, float] = {
    "northern_africa": 0.42,
    "eastern_africa": 0.38,
    "middle_africa": 0.28,
    "western_africa": 0.34,
    "southern_africa": 0.46,
    "eastern_asia": 0.62,
    "south_eastern_asia": 0.4,
    "southern_asia": 0.36,
    "central_asia": 0.4,
    "western_asia": 0.44,
    "western_europe": 0.72,
    "eastern_europe": 0.58,
    "northern_europe": 0.7,
    "southern_europe": 0.6,
    "northern_america": 0.68,
    "central_america": 0.4,
    "caribbean": 0.32,
    "south_america": 0.44,
    "australasia": 0.66,
    "melanesia": 0.3,
    "micronesia": 0.26,
    "polynesia": 0.28,
}

SUBREGION_CENTERS: dict[str, tuple[float, float]] = {
    "northern_africa": (9.5, 26.0),
    "eastern_africa": (40.0, 3.0),
    "middle_africa": (20.0, -1.0),
    "western_africa": (-1.0, 10.0),
    "southern_africa": (25.5, -22.5),
    "eastern_asia": (125.0, 36.0),
    "south_eastern_asia": (116.5, 6.5),
    "southern_asia": (79.0, 21.5),
    "central_asia": (67.0, 45.5),
    "western_asia": (46.0, 27.5),
    "western_europe": (2.0, 51.0),
    "eastern_europe": (30.0, 58.0),
    "northern_europe": (11.0, 63.0),
    "southern_europe": (10.0, 41.0),
    "northern_america": (-91.0, 42.0),
    "central_america": (-97.5, 20.0),
    "caribbean": (-72.0, 19.0),
    "south_america": (-58.0, -21.5),
    "australasia": (145.0, -29.0),
    "melanesia": (160.0, -11.0),
    "micronesia": (152.5, 11.0),
    "polynesia": (-152.5, -12.5),
}


def resolve_preset(macro: GeographyType, subregion: str | None) -> dict[str, object]:
    sid = resolve_subregion(macro, subregion)
    if sid in SUBREGION_PRESETS:
        preset = dict(SUBREGION_PRESETS[sid])
    else:
        fallback = CONTINENT_PRESETS.get(macro)
        preset = dict(fallback) if fallback else {
            "landform": LandformType.continent,
            "climate": ClimateType.temperate,
            "resource_pool": 100.0,
            "disaster_frequency": 0.2,
        }
    preset["sanitation"] = SANITATION.get(sid, 0.5)
    return preset
