import landRings from '~/data/landRings.json'
import physical from '~/data/physical.json'

const ELEV_W = 2048
const ELEV_H = 1024
let elevation: Uint8Array | null = null

export async function ensureElevation() {
  if (elevation) return
  const res = await fetch('/earth/elevation.bin')
  if (!res.ok) return
  elevation = new Uint8Array(await res.arrayBuffer())
}

export type Ring = [number, number][]

export type Theater = {
  id: string
  west: number
  east: number
  south: number
  north: number
}

export const THEATERS: Theater[] = [
  { id: 'asia', west: 60, east: 150, south: -10, north: 56 },
  { id: 'europe', west: -12, east: 42, south: 34, north: 72 },
  { id: 'middle_east', west: 26, east: 66, south: 12, north: 43 },
  { id: 'america', west: -125, east: -34, south: -56, north: 50 },
]

const THEATER_BY_ID: Record<string, Theater> = Object.fromEntries(THEATERS.map((item) => [item.id, item]))

const LAND = landRings as Ring[]
const LAKES = physical.lakes as Ring[]
const RIVERS = physical.rivers as { r: number; p: Ring }[]

export function lonLatToXy(lon: number, lat: number, w: number, h: number): [number, number] {
  return [((lon + 180) / 360) * w, ((90 - lat) / 180) * h]
}

function sampleElev(lon: number, lat: number) {
  if (!elevation || elevation.length < ELEV_W * ELEV_H) return 8
  const u = ((lon + 180) / 360) * ELEV_W
  const v = ((90 - lat) / 180) * (ELEV_H - 1)
  const x0 = ((Math.floor(u) % ELEV_W) + ELEV_W) % ELEV_W
  const x1 = (x0 + 1) % ELEV_W
  const y0 = Math.max(0, Math.min(ELEV_H - 2, Math.floor(v)))
  const y1 = y0 + 1
  const fx = u - Math.floor(u)
  const fy = v - y0
  const a = elevation[y0 * ELEV_W + x0]
  const b = elevation[y0 * ELEV_W + x1]
  const c = elevation[y1 * ELEV_W + x0]
  const d = elevation[y1 * ELEV_W + x1]
  return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy
}

function elevTint(e: number): [number, number, number] {
  const stops: [number, number, number, number][] = [
    [0, 228, 234, 212],
    [10, 210, 218, 184],
    [22, 192, 200, 162],
    [38, 174, 170, 140],
    [58, 156, 146, 122],
    [88, 140, 128, 110],
    [128, 148, 142, 134],
    [170, 176, 176, 174],
    [210, 214, 218, 220],
    [255, 236, 240, 242],
  ]
  let i = 0
  while (i < stops.length - 2 && e > stops[i + 1][0]) i += 1
  const lo = stops[i]
  const hi = stops[i + 1]
  const t = (e - lo[0]) / Math.max(1, hi[0] - lo[0])
  const s = t * t * (3 - 2 * t)
  return [lo[1] + (hi[1] - lo[1]) * s, lo[2] + (hi[2] - lo[2]) * s, lo[3] + (hi[3] - lo[3]) * s]
}

function pathRing(ctx: CanvasRenderingContext2D, ring: Ring, w: number, h: number, lonShift: number) {
  ctx.beginPath()
  ring.forEach(([lon, lat], i) => {
    const [x, y] = lonLatToXy(lon + lonShift, lat, w, h)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.closePath()
}

function drawRing(ctx: CanvasRenderingContext2D, ring: Ring, w: number, h: number, lonShift: number) {
  pathRing(ctx, ring, w, h, lonShift)
  ctx.fill()
}

function drawLine(ctx: CanvasRenderingContext2D, line: Ring, w: number, h: number, lonShift: number) {
  ctx.beginPath()
  line.forEach(([lon, lat], i) => {
    const [x, y] = lonLatToXy(lon + lonShift, lat, w, h)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.stroke()
}

function forWraps(fn: (shift: number) => void) {
  fn(0)
  fn(360)
  fn(-360)
}

export function pickTheater(geography: string | undefined, _seed = 0): Theater {
  if (geography && THEATER_BY_ID[geography]) return THEATER_BY_ID[geography]
  if (geography === 'continent') return THEATER_BY_ID.europe
  return THEATER_BY_ID.asia
}

export function theaterOutline(theater: Theater, steps = 72): Ring {
  const pts: Ring = []
  const { west, east, south, north } = theater
  for (let i = 0; i <= steps; i++) pts.push([west + ((east - west) * i) / steps, north])
  for (let i = 1; i <= steps; i++) pts.push([east, north - ((north - south) * i) / steps])
  for (let i = 1; i <= steps; i++) pts.push([east - ((east - west) * i) / steps, south])
  for (let i = 1; i <= steps; i++) pts.push([west, south + ((north - south) * i) / steps])
  return pts
}

export function simToLatLon(x: number, y: number, theater: Theater): { lat: number; lon: number } {
  return {
    lon: theater.west + (x / 100) * (theater.east - theater.west),
    lat: theater.north - (y / 100) * (theater.north - theater.south),
  }
}

export function theaterCenter(theater: Theater): { lat: number; lon: number } {
  return {
    lon: (theater.west + theater.east) / 2,
    lat: (theater.south + theater.north) / 2,
  }
}

export function theaterSpan(theater: Theater): number {
  return Math.max(theater.east - theater.west, theater.north - theater.south)
}

function shadeLand(color: HTMLCanvasElement, mask: HTMLCanvasElement, rough: HTMLCanvasElement) {
  const w = color.width
  const h = color.height
  const cctx = color.getContext('2d')
  const mctx = mask.getContext('2d')
  const rctx = rough.getContext('2d')
  if (!cctx || !mctx || !rctx) return
  const land = mctx.getImageData(0, 0, w, h).data
  const dst = cctx.getImageData(0, 0, w, h)
  const pix = dst.data
  const rimg = rctx.createImageData(w, h)
  const rp = rimg.data
  const idx = (x: number, y: number) => ((y * w + x) * 4)
  const isLand = (x: number, y: number) => {
    if (x < 0 || y < 0 || x >= w || y >= h) return false
    return land[idx(x, y)] > 16
  }
  for (let y = 0; y < h; y++) {
    const lat = 90 - (y / h) * 180
    for (let x = 0; x < w; x++) {
      const i = idx(x, y)
      if (!isLand(x, y)) {
        rp[i] = 48
        rp[i + 1] = 48
        rp[i + 2] = 48
        rp[i + 3] = 255
        continue
      }
      const lon = (x / w) * 360 - 180
      const e = sampleElev(lon, lat)
      let [lr, lg, lb] = elevTint(e)
      const coast =
        !isLand(x - 1, y) || !isLand(x + 1, y) || !isLand(x, y - 1) || !isLand(x, y + 1)
      if (coast) {
        lr = lr * 0.88 + 12
        lg = lg * 0.88 + 14
        lb = lb * 0.86 + 16
      }
      pix[i] = Math.max(0, Math.min(255, lr))
      pix[i + 1] = Math.max(0, Math.min(255, lg))
      pix[i + 2] = Math.max(0, Math.min(255, lb))
      pix[i + 3] = 255
      const roughV = 210
      rp[i] = roughV
      rp[i + 1] = roughV
      rp[i + 2] = roughV
      rp[i + 3] = 255
    }
  }
  cctx.putImageData(dst, 0, 0)
  rctx.putImageData(rimg, 0, 0)
}

export function createEarthCanvases(width = 4096) {
  const height = width / 2
  const color = document.createElement('canvas')
  color.width = width
  color.height = height
  const rough = document.createElement('canvas')
  rough.width = width
  rough.height = height
  const mask = document.createElement('canvas')
  mask.width = width
  mask.height = height
  const cctx = color.getContext('2d')
  const rctx = rough.getContext('2d')
  const mctx = mask.getContext('2d')
  if (!cctx || !rctx || !mctx) return { color, rough }

  const ocean = cctx.createLinearGradient(0, 0, 0, height)
  ocean.addColorStop(0, '#2a6890')
  ocean.addColorStop(0.22, '#1a5278')
  ocean.addColorStop(0.5, '#13425f')
  ocean.addColorStop(0.78, '#1a5278')
  ocean.addColorStop(1, '#2a6890')
  cctx.fillStyle = ocean
  cctx.fillRect(0, 0, width, height)

  for (let i = 0; i < 8; i++) {
    const y = ((i + 1) / 9) * height
    cctx.strokeStyle = 'rgba(140, 190, 220, 0.05)'
    cctx.lineWidth = 1
    cctx.beginPath()
    cctx.moveTo(0, y)
    cctx.lineTo(width, y)
    cctx.stroke()
  }
  for (let i = 0; i < 12; i++) {
    const x = (i / 12) * width
    cctx.strokeStyle = 'rgba(140, 190, 220, 0.04)'
    cctx.beginPath()
    cctx.moveTo(x, 0)
    cctx.lineTo(x, height)
    cctx.stroke()
  }

  mctx.fillStyle = '#000'
  mctx.fillRect(0, 0, width, height)
  mctx.fillStyle = '#fff'
  rctx.fillStyle = '#303030'
  rctx.fillRect(0, 0, width, height)

  for (const ring of LAND) {
    drawRing(mctx, ring, width, height, 0)
    drawRing(mctx, ring, width, height, 360)
    drawRing(mctx, ring, width, height, -360)
  }

  shadeLand(color, mask, rough)

  cctx.strokeStyle = 'rgba(12, 28, 22, 0.28)'
  cctx.lineWidth = Math.max(1, width / 2048)
  cctx.lineJoin = 'round'
  for (const ring of LAND) {
    pathRing(cctx, ring, width, height, 0)
    cctx.stroke()
  }

  cctx.fillStyle = '#1a5a7a'
  rctx.fillStyle = '#303030'
  for (const ring of LAKES) {
    forWraps((shift) => {
      drawRing(cctx, ring, width, height, shift)
      drawRing(rctx, ring, width, height, shift)
    })
  }

  cctx.lineCap = 'round'
  cctx.lineJoin = 'round'
  cctx.strokeStyle = 'rgba(110, 186, 214, 0.82)'
  for (const river of RIVERS) {
    const lw = Math.max(1.1, (5.2 - Math.min(river.r, 8) * 0.45) * (width / 4096))
    cctx.lineWidth = lw
    forWraps((shift) => drawLine(cctx, river.p, width, height, shift))
  }

  return { color, rough }
}
