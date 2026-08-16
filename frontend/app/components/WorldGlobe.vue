<script setup lang="ts">
import { Color, InstancedMesh, Object3D } from 'three'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { agentFill, settlementColor } from '~/utils/groupColors'
import {
  createEarthCanvases,
  ensureElevation,
  pickTheater,
  simToLatLon,
  theaterCenter,
  theaterOutline,
  theaterSpan,
  type Theater,
} from '~/utils/earthMap'

type GlobeAgent = {
  id: string
  name: string
  position: { x: number; y: number }
  wealth: number
  settlement_id: string | null
  alive: boolean
  traits?: string[]
}

type GlobeSettlement = {
  id: string
  position: { x: number; y: number }
  member_ids: string[]
  leader_id?: string | null
}

type GlobeSim = {
  world: { seed: number; geography?: string }
  agents: GlobeAgent[]
  settlements?: GlobeSettlement[]
}

const props = defineProps<{
  sim: GlobeSim | null
  geography: string
  seed: number
}>()

const { t } = useI18n()
const wrapRef = ref<HTMLElement | null>(null)
const panning = ref(false)
const zoomPct = ref(100)
const theaterId = ref('asia')

const MAX_MARKERS = 128
const EARTH_R = 1
const MARKER_R = 1.018

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let earth: THREE.Mesh | null = null
let earthMap: THREE.CanvasTexture | null = null
let roughMap: THREE.CanvasTexture | null = null
let theaterLine: THREE.Line | null = null
let agentsMesh: InstancedMesh | null = null
let halosMesh: InstancedMesh | null = null
let raf = 0
let disposed = false
const dummy = new Object3D()
const color = new Color()
let resizeObs: ResizeObserver | null = null

function latLonToVec(lat: number, lon: number, radius: number) {
  const u = (lon + 180) / 360
  const phi = u * Math.PI * 2
  const theta = ((90 - lat) * Math.PI) / 180
  const s = Math.sin(theta)
  return new THREE.Vector3(-radius * Math.cos(phi) * s, radius * Math.cos(theta), radius * Math.sin(phi) * s)
}

function activeTheater(): Theater {
  const geo = props.sim?.world.geography ?? props.geography
  const seed = props.sim?.world.seed ?? props.seed
  return pickTheater(geo, seed)
}

function distanceForTheater(theater: Theater) {
  return THREE.MathUtils.clamp(1.28 + (theaterSpan(theater) / 90) * 1.55, 1.32, 3.1)
}

function setZoomPct() {
  if (!camera) return
  const d = camera.position.length()
  zoomPct.value = Math.round(THREE.MathUtils.clamp(((4.8 - d) / (4.8 - 1.28)) * 160, 40, 220))
}

function zoomToward(clientX: number, clientY: number, factor: number) {
  if (!camera || !controls || !renderer) return
  const rect = renderer.domElement.getBoundingClientRect()
  const ndc = new THREE.Vector2(
    ((clientX - rect.left) / rect.width) * 2 - 1,
    -((clientY - rect.top) / rect.height) * 2 + 1,
  )
  const ray = new THREE.Raycaster()
  ray.setFromCamera(ndc, camera)
  const hit = earth ? ray.intersectObject(earth, false)[0] : undefined
  const dir = hit ? hit.point.clone().normalize() : camera.position.clone().normalize()
  const next = THREE.MathUtils.clamp(camera.position.length() * factor, controls.minDistance, controls.maxDistance)
  camera.position.copy(dir.multiplyScalar(next))
  controls.target.set(0, 0, 0)
  camera.lookAt(0, 0, 0)
  controls.update()
  setZoomPct()
}

function onGlobeDblClick(ev: MouseEvent) {
  ev.preventDefault()
  zoomToward(ev.clientX, ev.clientY, ev.shiftKey ? 1.45 : 0.62)
}

function zoomCenter(factor: number) {
  if (!renderer) return
  const rect = renderer.domElement.getBoundingClientRect()
  zoomToward(rect.left + rect.width / 2, rect.top + rect.height / 2, factor)
}

function zoomIn() {
  zoomCenter(0.72)
}

function zoomOut() {
  zoomCenter(1.38)
}

function lookAtLatLon(lat: number, lon: number, distance: number) {
  if (!camera || !controls) return
  const pos = latLonToVec(lat, lon, distance)
  camera.position.copy(pos)
  controls.target.set(0, 0, 0)
  camera.lookAt(0, 0, 0)
  controls.update()
  setZoomPct()
}

function applyEarth(theater: Theater) {
  if (!earth) return
  const { color: colorCanvas, rough } = createEarthCanvases()
  earthMap?.dispose()
  roughMap?.dispose()
  earthMap = new THREE.CanvasTexture(colorCanvas)
  roughMap = new THREE.CanvasTexture(rough)
  earthMap.colorSpace = THREE.SRGBColorSpace
  earthMap.wrapS = THREE.RepeatWrapping
  roughMap.wrapS = THREE.RepeatWrapping
  earthMap.anisotropy = renderer?.capabilities.getMaxAnisotropy() ?? 8
  earthMap.minFilter = THREE.LinearMipmapLinearFilter
  earthMap.magFilter = THREE.LinearFilter
  earthMap.generateMipmaps = true
  roughMap.anisotropy = earthMap.anisotropy
  const mat = earth.material as THREE.MeshStandardMaterial
  mat.map = earthMap
  mat.roughnessMap = roughMap
  mat.needsUpdate = true
  theaterId.value = theater.id
  updateTheaterLine(theater)
}

function updateTheaterLine(theater: Theater) {
  if (!scene) return
  if (theaterLine) {
    scene.remove(theaterLine)
    theaterLine.geometry.dispose()
    const mat = theaterLine.material
    if (!Array.isArray(mat)) mat.dispose()
    theaterLine = null
  }
  const pts = theaterOutline(theater).map(([lon, lat]) => latLonToVec(lat, lon, 1.006))
  const geo = new THREE.BufferGeometry().setFromPoints(pts)
  theaterLine = new THREE.LineLoop(
    geo,
    new THREE.LineBasicMaterial({ color: 0xffd678, transparent: true, opacity: 0.7 }),
  )
  scene.add(theaterLine)
}

function focusTheater(animateFit = false) {
  const theater = activeTheater()
  applyEarth(theater)
  const c = theaterCenter(theater)
  lookAtLatLon(c.lat, c.lon, distanceForTheater(theater))
  if (animateFit) fitToAgents()
}

function fitToAgents() {
  const current = props.sim
  const theater = activeTheater()
  const alive = (current?.agents ?? []).filter((a) => a.alive)
  if (!alive.length) {
    const c = theaterCenter(theater)
    lookAtLatLon(c.lat, c.lon, distanceForTheater(theater))
    return
  }
  let slat = 0
  let slon = 0
  for (const agent of alive) {
    const p = simToLatLon(agent.position.x, agent.position.y, theater)
    slat += p.lat
    slon += p.lon
  }
  lookAtLatLon(slat / alive.length, slon / alive.length, Math.min(distanceForTheater(theater), 1.7))
}

function resetView() {
  focusTheater()
}

function showWholeEarth() {
  const theater = activeTheater()
  const c = theaterCenter(theater)
  lookAtLatLon(c.lat, c.lon, 3.6)
}

function updateMarkers() {
  if (!agentsMesh || !halosMesh) return
  const theater = activeTheater()
  const current = props.sim
  const settlements = current?.settlements ?? []
  const leaders = new Set(settlements.map((s) => s.leader_id).filter((id): id is string => Boolean(id)))
  const alive = (current?.agents ?? []).filter((a) => a.alive)

  for (let i = 0; i < MAX_MARKERS; i++) {
    const agent = alive[i]
    if (!agent) {
      dummy.position.set(0, 0, 0)
      dummy.scale.setScalar(0)
      dummy.updateMatrix()
      agentsMesh.setMatrixAt(i, dummy.matrix)
      color.set('#000000')
      agentsMesh.setColorAt(i, color)
      continue
    }
    const { lat, lon } = simToLatLon(agent.position.x, agent.position.y, theater)
    const isLeader = leaders.has(agent.id)
    dummy.position.copy(latLonToVec(lat, lon, MARKER_R))
    dummy.scale.setScalar((isLeader ? 0.018 : 0.012) + Math.min(0.012, agent.wealth / 900))
    dummy.lookAt(0, 0, 0)
    dummy.updateMatrix()
    agentsMesh.setMatrixAt(i, dummy.matrix)
    color.set(agentFill(agent, isLeader))
    agentsMesh.setColorAt(i, color)
  }
  agentsMesh.instanceMatrix.needsUpdate = true
  if (agentsMesh.instanceColor) agentsMesh.instanceColor.needsUpdate = true

  for (let i = 0; i < MAX_MARKERS; i++) {
    const settlement = settlements[i]
    if (!settlement || settlement.member_ids.length < 2) {
      dummy.scale.setScalar(0)
      dummy.position.set(0, 0, 0)
      dummy.updateMatrix()
      halosMesh.setMatrixAt(i, dummy.matrix)
      continue
    }
    const { lat, lon } = simToLatLon(settlement.position.x, settlement.position.y, theater)
    dummy.position.copy(latLonToVec(lat, lon, 1.012))
    dummy.scale.setScalar(0.04 + settlement.member_ids.length * 0.004)
    dummy.updateMatrix()
    halosMesh.setMatrixAt(i, dummy.matrix)
    color.set(settlementColor(settlement.id))
    halosMesh.setColorAt(i, color)
  }
  halosMesh.instanceMatrix.needsUpdate = true
  if (halosMesh.instanceColor) halosMesh.instanceColor.needsUpdate = true
}

function resize() {
  const el = wrapRef.value
  if (!el || !renderer || !camera) return
  const w = Math.max(2, el.clientWidth)
  const h = Math.max(2, el.clientHeight)
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h, false)
}

function tickFrame() {
  if (disposed) return
  controls?.update()
  if (renderer && scene && camera) renderer.render(scene, camera)
  setZoomPct()
  raf = requestAnimationFrame(tickFrame)
}

async function init() {
  const el = wrapRef.value
  if (!el) return
  disposed = false
  await ensureElevation()
  if (disposed || !wrapRef.value) return
  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x04070c, 0.045)

  camera = new THREE.PerspectiveCamera(42, 1, 0.1, 40)
  camera.position.set(0, 0.4, 2.6)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearColor(0x04070c, 1)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.28
  renderer.domElement.className = 'globe-canvas'
  el.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0x8aa3c0, 0.62))
  const key = new THREE.DirectionalLight(0xfff6ea, 1.7)
  key.position.set(4, 2.2, 3)
  scene.add(key)
  const rim = new THREE.DirectionalLight(0x9ec8ff, 0.48)
  rim.position.set(-3.2, 0.4, -2.4)
  scene.add(rim)
  scene.add(new THREE.HemisphereLight(0xb6d6ff, 0x243830, 0.52))

  const starGeo = new THREE.BufferGeometry()
  const starPos = new Float32Array(2400 * 3)
  for (let i = 0; i < 2400; i++) {
    const r = 16 + Math.random() * 10
    const th = Math.random() * Math.PI * 2
    const ph = Math.acos(2 * Math.random() - 1)
    starPos[i * 3] = r * Math.sin(ph) * Math.cos(th)
    starPos[i * 3 + 1] = r * Math.cos(ph)
    starPos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th)
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3))
  scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xcfe4ff, size: 0.03, sizeAttenuation: true })))

  const { color: colorCanvas, rough } = createEarthCanvases()
  earthMap = new THREE.CanvasTexture(colorCanvas)
  roughMap = new THREE.CanvasTexture(rough)
  earthMap.colorSpace = THREE.SRGBColorSpace
  earthMap.wrapS = THREE.RepeatWrapping
  roughMap.wrapS = THREE.RepeatWrapping
  earth = new THREE.Mesh(
    new THREE.SphereGeometry(EARTH_R, 192, 128),
    new THREE.MeshStandardMaterial({
      map: earthMap,
      roughnessMap: roughMap,
      roughness: 1,
      metalness: 0,
    }),
  )
  scene.add(earth)

  const atmosVert = `
        varying vec3 vNormal;
        varying vec3 vView;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          vView = normalize(-mv.xyz);
          gl_Position = projectionMatrix * mv;
        }
      `
  scene.add(
    new THREE.Mesh(
      new THREE.SphereGeometry(1.048, 64, 48),
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        transparent: true,
        depthWrite: false,
        vertexShader: atmosVert,
        fragmentShader: `
        varying vec3 vNormal;
        varying vec3 vView;
        void main() {
          float f = pow(0.62 - dot(vNormal, vView), 3.2);
          gl_FragColor = vec4(0.40, 0.64, 1.0, clamp(f * 0.35, 0.0, 0.22));
        }
      `,
      }),
    ),
  )
  scene.add(
    new THREE.Mesh(
      new THREE.SphereGeometry(1.012, 64, 48),
      new THREE.ShaderMaterial({
        side: THREE.FrontSide,
        transparent: true,
        depthWrite: false,
        vertexShader: atmosVert,
        fragmentShader: `
        varying vec3 vNormal;
        varying vec3 vView;
        void main() {
          float f = pow(1.0 - max(dot(vNormal, vView), 0.0), 5.0);
          gl_FragColor = vec4(0.50, 0.74, 1.0, clamp(f * 0.14, 0.0, 0.1));
        }
      `,
      }),
    ),
  )

  agentsMesh = new InstancedMesh(
    new THREE.SphereGeometry(1, 12, 10),
    new THREE.MeshStandardMaterial({ roughness: 0.35, metalness: 0.1, emissive: 0x111111 }),
    MAX_MARKERS,
  )
  agentsMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
  scene.add(agentsMesh)

  halosMesh = new InstancedMesh(
    new THREE.SphereGeometry(1, 16, 12),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.38, depthWrite: false }),
    MAX_MARKERS,
  )
  halosMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
  scene.add(halosMesh)
  for (let i = 0; i < MAX_MARKERS; i++) {
    dummy.scale.setScalar(0)
    dummy.updateMatrix()
    agentsMesh.setMatrixAt(i, dummy.matrix)
    halosMesh.setMatrixAt(i, dummy.matrix)
    color.set('#000')
    agentsMesh.setColorAt(i, color)
    halosMesh.setColorAt(i, color)
  }

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enablePan = false
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.rotateSpeed = 0.55
  controls.zoomSpeed = 0.85
  controls.minDistance = 1.28
  controls.maxDistance = 4.8
  controls.target.set(0, 0, 0)
  renderer.domElement.addEventListener('pointerdown', () => {
    panning.value = true
  })
  renderer.domElement.addEventListener('dblclick', onGlobeDblClick)
  window.addEventListener('pointerup', () => {
    panning.value = false
  })

  resizeObs = new ResizeObserver(resize)
  resizeObs.observe(el)
  resize()
  focusTheater()
  updateMarkers()
  tickFrame()
}

function dispose() {
  disposed = true
  cancelAnimationFrame(raf)
  resizeObs?.disconnect()
  resizeObs = null
  controls?.dispose()
  earthMap?.dispose()
  roughMap?.dispose()
  renderer?.domElement.removeEventListener('dblclick', onGlobeDblClick)
  renderer?.dispose()
  renderer?.domElement.remove()
  scene?.clear()
  renderer = null
  scene = null
  camera = null
  controls = null
  earth = null
  theaterLine = null
  agentsMesh = null
  halosMesh = null
}

onMounted(() => {
  void init()
})
onBeforeUnmount(dispose)

watch(
  () => (props.sim ? `sim:${props.sim.world.geography}:${props.sim.world.seed}` : `draft:${props.geography}:${props.seed}`),
  () => {
    if (!earth) return
    if (props.sim) {
      applyEarth(activeTheater())
      fitToAgents()
    } else {
      focusTheater()
    }
    updateMarkers()
  },
)

watch(
  () => props.sim,
  () => updateMarkers(),
  { deep: true },
)

defineExpose({ fitToAgents, resetView, showWholeEarth })
</script>

<template>
  <div ref="wrapRef" class="map-wrap" :class="{ panning }">
    <div class="map-zoom">
      <span>{{ zoomPct }}%</span>
      <span class="theater-name">{{ t(`theaters.${theaterId}`) }}</span>
      <button type="button" class="map-zoom-btn" @click="fitToAgents">{{ t('map.fit') }}</button>
      <button type="button" class="map-zoom-btn" @click="showWholeEarth">{{ t('map.world') }}</button>
      <button type="button" class="map-zoom-btn" @click="resetView">{{ t('map.reset') }}</button>
      <button type="button" class="map-zoom-pm" :aria-label="t('map.zoomOut')" @click="zoomOut">−</button>
      <button type="button" class="map-zoom-pm" :aria-label="t('map.zoomIn')" @click="zoomIn">+</button>
      <button type="button" class="map-zoom-pm" :aria-label="t('map.fitAll')" @click="showWholeEarth">⛶</button>
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
  background: #04070c;
  cursor: grab;
  touch-action: none;
}

.map-wrap.panning {
  cursor: grabbing;
}

.map-wrap :deep(.globe-canvas) {
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
