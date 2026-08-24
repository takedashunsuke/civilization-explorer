<script setup lang="ts">
import { agentFill, hexRgba, polityKind, settlementColor } from '~/utils/groupColors'
import {
  createEarthCanvases,
  ensureElevation,
  lonLatToXy,
  pickTheater,
  simToLatLon,
  snapLonLatToLand,
  theaterCenter,
  CONTINENT_THEATERS,
  type Theater,
} from '~/utils/earthMap'

type MapAgent = {
  id: string
  position: { x: number; y: number }
  wealth: number
  settlement_id: string | null
  alive: boolean
  traits?: string[]
  region_id?: string | null
  subregion_id?: string | null
}

type MapSettlement = {
  id: string
  position: { x: number; y: number }
  member_ids: string[]
  leader_id?: string | null
  region_id?: string | null
  subregion_id?: string | null
}

type MapEvent = {
  turn: number
  actor_id: string
  action: string
  target_id?: string | null
  detail_key?: string
  lon?: number | null
  lat?: number | null
  alert?: string | null
}

type MapSim = {
  world: {
    seed: number
    geography?: string
    landform?: string
    climate?: string
    turn?: number
    regions?: Array<{ id: string; climate?: string; subregion_id?: string | null }>
  }
  agents: MapAgent[]
  settlements?: MapSettlement[]
  events?: MapEvent[]
}

const props = defineProps<{
  sim: MapSim | null
  geography: string
  landform?: string
  climate?: string
  seed: number
}>()

const { t } = useI18n()
const wrapRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const panning = ref(false)
const zoomPct = ref(100)
const theaterId = ref('world')

const MIN_SCALE = 0.12
const MAX_SCALE = 18
/** 南極側。イベントが少ないので既定の全体表示から外す */
const SOUTH_CROP = 0.1

let earthCanvas: HTMLCanvasElement | null = null
let landMask: HTMLCanvasElement | null = null
let overlayCanvas: HTMLCanvasElement | null = null
let scale = 1
let ox = 0
let oy = 0
let drag: { x: number; y: number; ox: number; oy: number } | null = null
let raf = 0
let disposed = false
let resizeObs: ResizeObserver | null = null
let builtKey = ''

function theaterFor(id?: string | null): Theater {
  return pickTheater(id || 'asia')
}

function agentTheater(agent: { region_id?: string | null; subregion_id?: string | null }): Theater {
  return theaterFor(agent.subregion_id || agent.region_id)
}

function projectOnLand(x: number, y: number, theater: Theater, earth: HTMLCanvasElement): [number, number] {
  const raw = simToLatLon(x, y, theater)
  const snapped = snapLonLatToLand(raw.lon, raw.lat, landMask, theater)
  return lonLatToXy(snapped.lon, snapped.lat, earth.width, earth.height)
}

function projectAgent(agent: { position: { x: number; y: number }; region_id?: string | null; subregion_id?: string | null }, earth: HTMLCanvasElement): [number, number] {
  return projectOnLand(agent.position.x, agent.position.y, agentTheater(agent), earth)
}

function viewSize() {
  const el = wrapRef.value
  const canvas = canvasRef.value
  if (!el || !canvas) return { w: 2, h: 2, dpr: 1 }
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const w = Math.max(2, el.clientWidth)
  const h = Math.max(2, el.clientHeight)
  if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
    canvas.width = Math.floor(w * dpr)
    canvas.height = Math.floor(h * dpr)
    canvas.style.width = `${w}px`
    canvas.style.height = `${h}px`
  }
  return { w: canvas.width, h: canvas.height, dpr }
}

function setZoomPct() {
  zoomPct.value = Math.round(Math.min(220, Math.max(40, scale * 55)))
}

function fitRect(x: number, y: number, bw: number, bh: number, pad = 0.9) {
  if (!earthCanvas) return
  const { w, h } = viewSize()
  const next = Math.min(w / Math.max(bw, 1), h / Math.max(bh, 1)) * pad
  scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, next))
  ox = w / 2 - (x + bw / 2) * scale
  oy = h / 2 - (y + bh / 2) * scale
  setZoomPct()
}

function fitTheater() {
  if (!earthCanvas) return
  theaterId.value = 'world'
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const theater of CONTINENT_THEATERS) {
    const [x1, y1] = lonLatToXy(theater.west, theater.north, earthCanvas.width, earthCanvas.height)
    const [x2, y2] = lonLatToXy(theater.east, theater.south, earthCanvas.width, earthCanvas.height)
    minX = Math.min(minX, x1, x2)
    minY = Math.min(minY, y1, y2)
    maxX = Math.max(maxX, x1, x2)
    maxY = Math.max(maxY, y1, y2)
  }
  fitRect(minX, minY, Math.max(8, maxX - minX), Math.max(8, maxY - minY), 0.9)
}

function showWorld() {
  if (!earthCanvas) return
  theaterId.value = 'world'
  const usableH = earthCanvas.height * (1 - SOUTH_CROP)
  fitRect(0, 0, earthCanvas.width, usableH, 1)
}

function fitToAgents() {
  if (!earthCanvas) return
  const alive = (props.sim?.agents ?? []).filter((a) => a.alive)
  if (!alive.length) {
    fitTheater()
    return
  }
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const agent of alive) {
    const [x, y] = projectAgent(agent, earthCanvas)
    minX = Math.min(minX, x)
    minY = Math.min(minY, y)
    maxX = Math.max(maxX, x)
    maxY = Math.max(maxY, y)
  }
  const pad = Math.max(24, (maxX - minX) * 0.2)
  fitRect(minX - pad, minY - pad, maxX - minX + pad * 2, maxY - minY + pad * 2, 0.9)
}

async function rebuildEarth() {
  await ensureElevation()
  if (disposed) return
  if (builtKey === 'earth' && earthCanvas) {
    theaterId.value = 'world'
    return
  }
  const { color, mask } = createEarthCanvases(4096)
  earthCanvas = color
  landMask = mask
  builtKey = 'earth'
  theaterId.value = 'world'
  showWorld()
}

function draw() {
  const canvas = canvasRef.value
  const earth = earthCanvas
  if (!canvas || !earth) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const { w, h } = viewSize()
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.fillStyle = '#071018'
  ctx.fillRect(0, 0, w, h)
  ctx.setTransform(scale, 0, 0, scale, ox, oy)
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(earth, 0, 0)

  const climateByRegion = Object.fromEntries(
    (props.sim?.world.regions ?? []).map((region) => [region.id, region.climate ?? 'temperate']),
  )
  const tint: Record<string, string | null> = {
    temperate: null,
    cold: 'rgba(186, 214, 238, 0.22)',
    wetland: 'rgba(64, 130, 88, 0.18)',
    arid: 'rgba(214, 176, 96, 0.2)',
  }
  for (const theater of CONTINENT_THEATERS) {
    const [x1, y1] = lonLatToXy(theater.west, theater.north, earth.width, earth.height)
    const [x2, y2] = lonLatToXy(theater.east, theater.south, earth.width, earth.height)
    const overlay = tint[climateByRegion[theater.id] ?? 'temperate']
    if (overlay) {
      ctx.fillStyle = overlay
      ctx.fillRect(x1, y1, x2 - x1, y2 - y1)
    }
    ctx.strokeStyle = 'rgba(255, 214, 120, 0.35)'
    ctx.lineWidth = 1.1 / scale
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
  }
  for (const region of props.sim?.world.regions ?? []) {
    const theater = pickTheater(region.subregion_id || region.id)
    const [x1, y1] = lonLatToXy(theater.west, theater.north, earth.width, earth.height)
    const [x2, y2] = lonLatToXy(theater.east, theater.south, earth.width, earth.height)
    ctx.strokeStyle = 'rgba(255, 236, 170, 0.95)'
    ctx.lineWidth = 1.8 / scale
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
  }

  const settlements = props.sim?.settlements ?? []
  const agentsById = new Map((props.sim?.agents ?? []).map((a) => [a.id, a]))
  const leaders = new Set(settlements.map((s) => s.leader_id).filter((id): id is string => Boolean(id)))
  const centers = new Map<string, [number, number]>()

  if (!overlayCanvas) overlayCanvas = document.createElement('canvas')
  if (overlayCanvas.width !== w || overlayCanvas.height !== h) {
    overlayCanvas.width = w
    overlayCanvas.height = h
  }
  const octx = overlayCanvas.getContext('2d')
  if (octx) {
    octx.setTransform(1, 0, 0, 1, 0, 0)
    octx.clearRect(0, 0, w, h)
    octx.setTransform(scale, 0, 0, scale, ox, oy)
  }

  for (const settlement of settlements) {
    if (settlement.member_ids.length < 2) continue
    const pts: Array<[number, number]> = []
    for (const id of settlement.member_ids) {
      const agent = agentsById.get(id)
      if (!agent?.alive) continue
      pts.push(projectAgent(agent, earth))
    }
    const member = pts.length
      ? agentsById.get(settlement.member_ids.find((id) => agentsById.get(id)?.alive) ?? '')
      : undefined
    const center = member
      ? projectAgent(member, earth)
      : projectOnLand(settlement.position.x, settlement.position.y, theaterFor(settlement.subregion_id || settlement.region_id), earth)
    centers.set(settlement.id, center)
    const hull = convexHull(pts)
    const color = settlementColor(settlement.region_id || settlement.id)
    const target = octx ?? ctx
    target.beginPath()
    if (hull.length >= 3) {
      target.moveTo(hull[0][0], hull[0][1])
      for (let i = 1; i < hull.length; i++) target.lineTo(hull[i][0], hull[i][1])
      target.closePath()
    } else {
      const spread = pts.length
        ? Math.max(14, ...pts.map(([x, y]) => Math.hypot(x - center[0], y - center[1])))
        : 18
      target.arc(center[0], center[1], spread + 8, 0, Math.PI * 2)
    }
    target.fillStyle = hexRgba(color, 0.22)
    target.fill()
    target.strokeStyle = color
    target.lineWidth = (1.6 + Math.min(3, settlement.member_ids.length / 8)) / scale
    target.stroke()
  }

  if (octx && landMask) {
    octx.globalCompositeOperation = 'destination-in'
    octx.drawImage(landMask, 0, 0)
    octx.globalCompositeOperation = 'source-over'
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.drawImage(overlayCanvas, 0, 0)
    ctx.setTransform(scale, 0, 0, scale, ox, oy)
  }

  const turn = props.sim?.world.turn
  const clashes = (props.sim?.events ?? []).filter(
    (e) =>
      e.turn === turn &&
      e.action === 'conflict' &&
      e.target_id &&
      centers.has(e.actor_id) &&
      centers.has(e.target_id),
  )
  for (const clash of clashes) {
    const a = centers.get(clash.actor_id)
    const b = centers.get(clash.target_id as string)
    if (!a || !b) continue
    ctx.beginPath()
    ctx.moveTo(a[0], a[1])
    ctx.lineTo(b[0], b[1])
    ctx.strokeStyle = 'rgba(255, 92, 72, 0.85)'
    ctx.lineWidth = 2.2 / scale
    ctx.setLineDash([6 / scale, 4 / scale])
    ctx.stroke()
    ctx.setLineDash([])
  }

  const alive = (props.sim?.agents ?? []).filter((a) => a.alive).slice(0, 128)
  for (const agent of alive) {
    const [x, y] = projectAgent(agent, earth)
    const isLeader = leaders.has(agent.id)
    const r = (isLeader ? 5.5 : 4) + Math.min(4, agent.wealth / 250)
    ctx.beginPath()
    ctx.arc(x, y, r / scale, 0, Math.PI * 2)
    ctx.fillStyle = agentFill(agent, isLeader)
    ctx.fill()
    ctx.lineWidth = 1 / scale
    ctx.strokeStyle = 'rgba(8, 12, 16, 0.55)'
    ctx.stroke()
  }

  ctx.font = `${11 / scale}px ui-sans-serif, system-ui, sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'bottom'
  for (const settlement of settlements) {
    if (settlement.member_ids.length < 2) continue
    const center = centers.get(settlement.id)
    if (!center) continue
    const kind = polityKind(settlement.member_ids.length)
    const label = `${t(`map.polity.${kind}`)} · ${settlement.member_ids.length}`
    ctx.fillStyle = 'rgba(8, 12, 16, 0.65)'
    ctx.fillText(label, center[0], center[1] - 7 / scale)
    ctx.fillStyle = settlementColor(settlement.region_id || settlement.id)
    ctx.fillText(label, center[0], center[1] - 8 / scale)
  }

  const pulseTurn = (props.sim?.world.turn ?? 1) - 1
  const pulseAt = Date.now() / 260
  for (const ev of props.sim?.events ?? []) {
    if (!ev.alert || ev.turn !== pulseTurn) continue
    let lon = ev.lon
    let lat = ev.lat
    if (lon == null || lat == null) {
      const mid = theaterCenter(pickTheater(ev.actor_id || 'asia'))
      lon = mid.lon
      lat = mid.lat
    }
    const [x, y] = lonLatToXy(lon, lat, earth.width, earth.height)
    const blink = 0.28 + 0.42 * (0.5 + 0.5 * Math.sin(pulseAt))
    const radius = (42 + 16 * (0.5 + 0.5 * Math.sin(pulseAt * 1.35))) / scale
    const color = ev.alert === 'red' ? `255, 72, 64` : `255, 214, 64`
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.strokeStyle = `rgba(${color}, ${blink})`
    ctx.lineWidth = 3.4 / scale
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(x, y, 7 / scale, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${color}, ${0.45 + blink * 0.4})`
    ctx.fill()
  }
}

function convexHull(points: Array<[number, number]>): Array<[number, number]> {
  const pts = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1])
  if (pts.length <= 2) return pts
  const cross = (o: [number, number], a: [number, number], b: [number, number]) =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
  const lower: Array<[number, number]> = []
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop()
    lower.push(p)
  }
  const upper: Array<[number, number]> = []
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i]
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop()
    upper.push(p)
  }
  lower.pop()
  upper.pop()
  return lower.concat(upper)
}

function tick() {
  if (disposed) return
  draw()
  raf = requestAnimationFrame(tick)
}

function zoomAt(clientX: number, clientY: number, factor: number) {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const { dpr } = viewSize()
  const sx = (clientX - rect.left) * dpr
  const sy = (clientY - rect.top) * dpr
  const wx = (sx - ox) / scale
  const wy = (sy - oy) / scale
  scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale * factor))
  ox = sx - wx * scale
  oy = sy - wy * scale
  setZoomPct()
}

function zoomCenter(factor: number) {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, factor)
}

function zoomIn() {
  zoomCenter(1.22)
}

function zoomOut() {
  zoomCenter(0.82)
}

function onPointerDown(ev: PointerEvent) {
  panning.value = true
  drag = { x: ev.clientX, y: ev.clientY, ox, oy }
  ;(ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId)
}

function onPointerMove(ev: PointerEvent) {
  if (!drag) return
  const { dpr } = viewSize()
  ox = drag.ox + (ev.clientX - drag.x) * dpr
  oy = drag.oy + (ev.clientY - drag.y) * dpr
}

function onPointerUp() {
  panning.value = false
  drag = null
}

function onWheel(ev: WheelEvent) {
  ev.preventDefault()
  zoomAt(ev.clientX, ev.clientY, ev.deltaY > 0 ? 0.86 : 1.16)
}

function onDblClick(ev: MouseEvent) {
  ev.preventDefault()
  zoomAt(ev.clientX, ev.clientY, ev.shiftKey ? 0.62 : 1.55)
}

async function init() {
  disposed = false
  await rebuildEarth()
  if (disposed) return
  resizeObs = new ResizeObserver(() => {
    viewSize()
  })
  if (wrapRef.value) resizeObs.observe(wrapRef.value)
  tick()
}

function dispose() {
  disposed = true
  cancelAnimationFrame(raf)
  resizeObs?.disconnect()
  resizeObs = null
}

onMounted(() => {
  void init()
})
onBeforeUnmount(dispose)

watch(
  () => (props.sim ? `sim:${props.sim.world.geography}:${props.sim.world.seed}` : `draft:${props.geography}:${props.seed}`),
  () => {
    builtKey = ''
    void rebuildEarth()
  },
)
</script>

<template>
  <div ref="wrapRef" class="map-wrap" :class="{ panning }">
    <canvas
      ref="canvasRef"
      class="flat-canvas"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @wheel="onWheel"
      @dblclick="onDblClick"
    />
    <div class="map-zoom">
      <span>{{ zoomPct }}%</span>
      <span class="theater-name">{{ t(`theaters.${theaterId}`) }}</span>
      <button type="button" class="map-zoom-btn" @click="fitToAgents">{{ t('map.fit') }}</button>
      <button type="button" class="map-zoom-btn" @click="showWorld">{{ t('map.world') }}</button>
      <button type="button" class="map-zoom-btn" @click="fitTheater">{{ t('map.reset') }}</button>
      <button type="button" class="map-zoom-pm" :aria-label="t('map.zoomOut')" @click="zoomOut">−</button>
      <button type="button" class="map-zoom-pm" :aria-label="t('map.zoomIn')" @click="zoomIn">+</button>
      <button type="button" class="map-zoom-pm" :aria-label="t('map.fitAll')" @click="showWorld">⛶</button>
    </div>
  </div>
</template>

<style scoped>
.map-wrap {
  position: relative;
  flex: 1 1 auto;
  width: 100%;
  min-height: 280px;
  z-index: 1;
  overscroll-behavior: none;
  user-select: none;
  border-radius: 8px;
  border: 1px solid var(--line);
  overflow: hidden;
  background: #071018;
  cursor: grab;
  touch-action: none;
}

.map-wrap.panning {
  cursor: grabbing;
}

.flat-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.map-zoom {
  position: absolute;
  right: 0.5rem;
  bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.35rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 88%, #000);
  border: 1px solid var(--line);
  color: var(--text);
  font-size: 0.72rem;
  font-variant-numeric: tabular-nums;
  z-index: 2;
}

.theater-name {
  opacity: 0.85;
}

.map-zoom-btn {
  margin: 0;
  border: 0;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.map-zoom-btn:hover {
  color: var(--text);
  background: color-mix(in srgb, var(--line) 55%, transparent);
}

.map-zoom-pm {
  margin: 0;
  min-width: 1.45rem;
  border: 1px solid var(--line);
  background: color-mix(in srgb, var(--line) 35%, transparent);
  color: var(--text);
  cursor: pointer;
  padding: 0.08rem 0.35rem;
  border-radius: 4px;
  font-size: 0.95rem;
  line-height: 1.1;
}

.map-zoom-pm:hover {
  background: color-mix(in srgb, var(--line) 60%, transparent);
}
</style>
