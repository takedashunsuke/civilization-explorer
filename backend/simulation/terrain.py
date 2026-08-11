from __future__ import annotations

import math
import random

from simulation.models import GeographyType, Position, TerrainState

TERRAIN_COLS = 48
TERRAIN_ROWS = 48
LAND_BIOMES = ("coast", "river", "plain", "mountain")


def _hash_noise(ix: int, iy: int, seed: int) -> float:
    n = (ix * 374761393 + iy * 668265263 + seed * 1274126177) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n ^ (n >> 16)) / 4294967295.0


def _value_noise(x: float, y: float, seed: int) -> float:
    x0 = math.floor(x)
    y0 = math.floor(y)
    fx = x - x0
    fy = y - y0
    ux = fx * fx * (3.0 - 2.0 * fx)
    uy = fy * fy * (3.0 - 2.0 * fy)
    v00 = _hash_noise(x0, y0, seed)
    v10 = _hash_noise(x0 + 1, y0, seed)
    v01 = _hash_noise(x0, y0 + 1, seed)
    v11 = _hash_noise(x0 + 1, y0 + 1, seed)
    return (v00 * (1 - ux) + v10 * ux) * (1 - uy) + (v01 * (1 - ux) + v11 * ux) * uy


def _fbm(x: float, y: float, seed: int, octaves: int = 4) -> float:
    total = 0.0
    amp = 1.0
    freq = 3.0
    norm = 0.0
    for i in range(octaves):
        total += amp * _value_noise(x * freq, y * freq, seed + i * 101)
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm if norm else 0.0


def _in_ellipse(wx: float, wy: float, cx: float, cy: float, rx: float, ry: float, rot: float) -> float:
    dx, dy = wx - cx, wy - cy
    ca, sa = math.cos(rot), math.sin(rot)
    lx = dx * ca + dy * sa
    ly = -dx * sa + dy * ca
    return (lx / max(rx, 0.1)) ** 2 + (ly / max(ry, 0.1)) ** 2


def _neighbors(col: int, row: int, cols: int, rows: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nc, nr = col + dc, row + dr
        if 0 <= nc < cols and 0 <= nr < rows:
            out.append((nc, nr))
    return out


def generate_terrain(geography: GeographyType, seed: int) -> TerrainState:
    rng = random.Random(seed * 9176 + 13)
    cols, rows = TERRAIN_COLS, TERRAIN_ROWS
    land = [[False] * cols for _ in range(rows)]
    elev = [[0.0] * cols for _ in range(rows)]
    nseed = rng.randint(1, 10**9)

    if geography == GeographyType.island:
        blobs: list[tuple[float, float, float, float, float]] = []
        n_islands = rng.randint(3, 4)
        for i in range(n_islands):
            t = (i + 0.5) / n_islands
            blobs.append(
                (
                    26 + t * 46 + rng.uniform(-5, 5),
                    80 - t * 54 + rng.uniform(-5, 5),
                    rng.uniform(9, 15),
                    rng.uniform(12, 20),
                    rng.uniform(-0.45, 0.45),
                )
            )
        if rng.random() < 0.65:
            blobs.append((rng.uniform(14, 28), rng.uniform(14, 28), rng.uniform(3.5, 5.5), rng.uniform(4, 6), 0.0))

        for row in range(rows):
            for col in range(cols):
                wx = (col + 0.5) / cols * 100
                wy = (row + 0.5) / rows * 100
                dmin = min(_in_ellipse(wx, wy, *blob) for blob in blobs)
                n = _fbm(wx / 100, wy / 100, nseed)
                if dmin < 1.0 + (n - 0.5) * 0.38:
                    land[row][col] = True
                    elev[row][col] = max(0.0, 1.0 - dmin) * 0.72 + n * 0.28
    else:
        ocean_side = rng.choice(("w", "e", "n", "s"))
        gulf = rng.random() < 0.75
        gulf_pos = rng.uniform(0.28, 0.72)
        gulf_w = rng.uniform(0.12, 0.22)

        for row in range(rows):
            for col in range(cols):
                u = (col + 0.5) / cols
                v = (row + 0.5) / rows
                n = _fbm(u, v, nseed)
                if ocean_side == "w":
                    inland = u
                    along = v
                elif ocean_side == "e":
                    inland = 1.0 - u
                    along = v
                elif ocean_side == "n":
                    inland = v
                    along = u
                else:
                    inland = 1.0 - v
                    along = u
                if gulf and abs(along - gulf_pos) < gulf_w:
                    inland -= (1.0 - abs(along - gulf_pos) / gulf_w) * 0.3
                inland += (n - 0.5) * 0.2
                if inland > 0.2:
                    land[row][col] = True
                    elev[row][col] = (inland - 0.2) * 0.85 + n * 0.35

    biomes = [["ocean"] * cols for _ in range(rows)]
    for row in range(rows):
        for col in range(cols):
            if not land[row][col]:
                continue
            near_ocean = any(not land[nr][nc] for nc, nr in _neighbors(col, row, cols, rows))
            mountain_cut = 0.74 if geography == GeographyType.island else 0.64
            if elev[row][col] > mountain_cut and not near_ocean:
                biomes[row][col] = "mountain"
            else:
                biomes[row][col] = "plain"

    _carve_rivers(biomes, elev, land, rng)
    for row in range(rows):
        for col in range(cols):
            if biomes[row][col] != "plain":
                continue
            if any(biomes[nr][nc] == "ocean" for nc, nr in _neighbors(col, row, cols, rows)):
                biomes[row][col] = "coast"

    return TerrainState(
        cols=cols,
        rows=rows,
        biomes=[cell for row in biomes for cell in row],
    )


def _carve_rivers(
    biomes: list[list[str]],
    elev: list[list[float]],
    land: list[list[bool]],
    rng: random.Random,
) -> None:
    rows = len(biomes)
    cols = len(biomes[0])
    mountains = [(c, r) for r in range(rows) for c in range(cols) if biomes[r][c] == "mountain"]
    if not mountains:
        return
    rng.shuffle(mountains)
    sources = mountains[: rng.randint(3, 6)]
    for start in sources:
        col, row = start
        seen: set[tuple[int, int]] = set()
        for _ in range(cols + rows):
            if (col, row) in seen:
                break
            seen.add((col, row))
            if biomes[row][col] == "ocean":
                break
            if biomes[row][col] != "mountain":
                biomes[row][col] = "river"
            neigh = _neighbors(col, row, cols, rows)
            if not neigh:
                break
            nxt = min(neigh, key=lambda p: elev[p[1]][p[0]] if land[p[1]][p[0]] else -0.1)
            if land[nxt[1]][nxt[0]] and elev[nxt[1]][nxt[0]] > elev[row][col] + 0.02:
                oceanward = [p for p in neigh if not land[p[1]][p[0]]]
                if oceanward:
                    nxt = oceanward[0]
                else:
                    break
            col, row = nxt


def biome_at(terrain: TerrainState | None, x: float, y: float) -> str:
    if terrain is None or not terrain.biomes:
        return "plain"
    col = min(terrain.cols - 1, max(0, int(x / 100.0 * terrain.cols)))
    row = min(terrain.rows - 1, max(0, int(y / 100.0 * terrain.rows)))
    idx = row * terrain.cols + col
    if 0 <= idx < len(terrain.biomes):
        return terrain.biomes[idx]
    return "ocean"


def _tile_center(terrain: TerrainState, col: int, row: int) -> tuple[float, float]:
    return ((col + 0.5) / terrain.cols) * 100.0, ((row + 0.5) / terrain.rows) * 100.0


def _land_cells(terrain: TerrainState, preferred: tuple[str, ...] | None = None) -> list[tuple[int, int]]:
    wanted = preferred or LAND_BIOMES
    cells: list[tuple[int, int]] = []
    for idx, biome in enumerate(terrain.biomes):
        if biome not in wanted:
            continue
        cells.append((idx % terrain.cols, idx // terrain.cols))
    return cells


def random_land_position(
    terrain: TerrainState,
    rng: random.Random,
    geography: GeographyType | None = None,
) -> Position:
    preferred = ("coast", "river", "plain") if geography == GeographyType.island else ("plain", "river", "coast")
    cells = _land_cells(terrain, preferred) or _land_cells(terrain)
    if not cells:
        return Position(x=50.0, y=50.0)
    col, row = cells[rng.randrange(len(cells))]
    tw = 100.0 / terrain.cols
    th = 100.0 / terrain.rows
    cx, cy = _tile_center(terrain, col, row)
    return Position(
        x=min(99.5, max(0.5, cx + rng.uniform(-tw * 0.35, tw * 0.35))),
        y=min(99.5, max(0.5, cy + rng.uniform(-th * 0.35, th * 0.35))),
    )


def snap_to_land(terrain: TerrainState | None, x: float, y: float) -> Position:
    nx = min(99.5, max(0.5, x))
    ny = min(99.5, max(0.5, y))
    if terrain is None or biome_at(terrain, nx, ny) != "ocean":
        return Position(x=nx, y=ny)
    best: tuple[float, int, int] | None = None
    for idx, biome in enumerate(terrain.biomes):
        if biome not in LAND_BIOMES:
            continue
        col, row = idx % terrain.cols, idx // terrain.cols
        cx, cy = _tile_center(terrain, col, row)
        dist = (cx - nx) ** 2 + (cy - ny) ** 2
        if best is None or dist < best[0]:
            best = (dist, col, row)
    if best is None:
        return Position(x=50.0, y=50.0)
    cx, cy = _tile_center(terrain, best[1], best[2])
    return Position(x=cx, y=cy)
