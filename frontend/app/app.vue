<script setup lang="ts">
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

type Agent = {
  id: string
  name: string
  position: { x: number; y: number }
  wealth: number
  happiness: number
  settlement_id: string | null
  alive: boolean
}

type Metrics = {
  inequality: number
  mean_trust: number
  cooperation_rate: number
  authority: number
  mean_happiness: number
}

type EventRow = {
  turn: number
  actor_id: string
  action: string
  target_id?: string | null
  detail: string
  success?: boolean | null
}

type Simulation = {
  id: string
  status: string
  world: {
    turn: number
    seed: number
    tax_rate: number
    education_level: number
    institution: string
    resource_pool: number
  }
  agents: Agent[]
  events: EventRow[]
  last_metrics: Metrics | null
}

const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

const population = ref(8)
const seed = ref(42)
const taxRate = ref(0.1)
const education = ref(0.5)
const institution = ref('democracy')
const institutionOptions = [
  { label: 'democracy', value: 'democracy' },
  { label: 'autocracy', value: 'autocracy' },
  { label: 'anarchy', value: 'anarchy' },
]

const sim = ref<Simulation | null>(null)
const busy = ref(false)
const error = ref('')
const canvasRef = ref<HTMLCanvasElement | null>(null)

const recentEvents = computed(() => (sim.value?.events ?? []).slice(-30).reverse())

async function api<T>(path: string, options?: Parameters<typeof $fetch<T>>[1]): Promise<T> {
  return await $fetch<T>(`${apiBase}${path}`, options)
}

async function createSimulation() {
  busy.value = true
  error.value = ''
  try {
    sim.value = await api<Simulation>('/simulations', {
      method: 'POST',
      body: {
        seed: seed.value,
        population: population.value,
        tax_rate: taxRate.value,
        education_level: education.value,
        institution: institution.value,
        resource_pool: 100,
      },
    })
    await nextTick()
    drawMap()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

async function tick(n = 1) {
  if (!sim.value) return
  busy.value = true
  error.value = ''
  try {
    sim.value = await api<Simulation>(`/simulations/${sim.value.id}/tick`, {
      method: 'POST',
      body: { n },
    })
    await nextTick()
    drawMap()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

function settlementColor(id: string | null): string {
  if (!id) return '#8ab4f8'
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  const hue = hash % 360
  return `hsl(${hue} 65% 62%)`
}

function drawMap() {
  const canvas = canvasRef.value
  const current = sim.value
  if (!canvas || !current) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const w = canvas.width
  const h = canvas.height
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = '#101820'
  ctx.fillRect(0, 0, w, h)

  ctx.strokeStyle = '#243041'
  ctx.lineWidth = 1
  for (let i = 0; i <= 10; i++) {
    const x = (i / 10) * w
    const y = (i / 10) * h
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(w, y)
    ctx.stroke()
  }

  for (const agent of current.agents) {
    if (!agent.alive) continue
    const x = (agent.position.x / 100) * w
    const y = (agent.position.y / 100) * h
    const r = 5 + Math.min(8, agent.wealth / 4)
    ctx.beginPath()
    ctx.fillStyle = settlementColor(agent.settlement_id)
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#dce7f3'
    ctx.font = '11px sans-serif'
    ctx.fillText(agent.name, x + r + 2, y + 3)
  }
}

onMounted(() => {
  drawMap()
})

watch(sim, async () => {
  await nextTick()
  drawMap()
})
</script>

<template>
  <div class="layout">
    <header class="header">
      <div>
        <p class="eyebrow">Civilization Explorer</p>
        <h1>観測コンソール（スタブ）</h1>
      </div>
      <Tag v-if="sim" :value="`turn ${sim.world.turn} · ${sim.status}`" severity="info" />
    </header>

    <div class="grid">
      <aside class="panel">
        <h2>初期条件</h2>
        <label>人口</label>
        <InputNumber v-model="population" :min="2" :max="20" show-buttons class="w-full" />
        <label>seed</label>
        <InputNumber v-model="seed" show-buttons class="w-full" />
        <label>税率</label>
        <InputNumber v-model="taxRate" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="w-full" />
        <label>教育</label>
        <InputNumber v-model="education" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="w-full" />
        <label>制度</label>
        <Dropdown v-model="institution" :options="institutionOptions" option-label="label" option-value="value" class="w-full" />

        <div class="actions">
          <Button label="Create" icon="pi pi-plus" :loading="busy" @click="createSimulation" />
          <Button label="Tick" icon="pi pi-play" :disabled="!sim" :loading="busy" severity="success" @click="tick(1)" />
          <Button label="Tick ×5" icon="pi pi-forward" :disabled="!sim" :loading="busy" severity="help" @click="tick(5)" />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <div v-if="sim?.last_metrics" class="metrics">
          <h2>メトリクス</h2>
          <ul>
            <li>格差 {{ sim.last_metrics.inequality.toFixed(3) }}</li>
            <li>信頼 {{ sim.last_metrics.mean_trust.toFixed(3) }}</li>
            <li>協力率 {{ sim.last_metrics.cooperation_rate.toFixed(3) }}</li>
            <li>権威 {{ sim.last_metrics.authority.toFixed(3) }}</li>
            <li>幸福 {{ sim.last_metrics.mean_happiness.toFixed(3) }}</li>
          </ul>
        </div>
      </aside>

      <main class="viewport panel">
        <h2>2D マップ</h2>
        <canvas ref="canvasRef" width="720" height="520" class="map" />
      </main>

      <section class="panel events">
        <h2>Event</h2>
        <DataTable :value="recentEvents" size="small" scrollable scroll-height="520px">
          <Column field="turn" header="t" style="width: 3rem" />
          <Column field="actor_id" header="actor" />
          <Column field="action" header="action" />
          <Column field="detail" header="detail" />
        </DataTable>
      </section>
    </div>
  </div>
</template>

<style scoped>
.layout {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.25rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  margin-bottom: 1rem;
}

.eyebrow {
  margin: 0;
  color: var(--muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.75rem;
}

h1 {
  margin: 0.2rem 0 0;
  font-size: 1.5rem;
  font-weight: 650;
}

h2 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: var(--muted);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: 260px 1fr 340px;
  gap: 1rem;
}

.panel {
  background: color-mix(in srgb, var(--panel) 92%, transparent);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1rem;
}

label {
  display: block;
  margin: 0.7rem 0 0.25rem;
  color: var(--muted);
  font-size: 0.8rem;
}

.w-full {
  width: 100%;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.metrics ul {
  margin: 0;
  padding-left: 1rem;
  color: var(--text);
  line-height: 1.7;
}

.map {
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid var(--line);
  display: block;
}

.error {
  color: #ff8f8f;
  font-size: 0.85rem;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
