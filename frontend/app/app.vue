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

const { t, locale, setLocale } = useI18n()
const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

const population = ref(8)
const seed = ref(42)
const taxRate = ref(0.1)
const education = ref(0.5)
/** API には英語キーのまま送る */
const institution = ref('democracy')

const institutionOptions = computed(() => [
  { label: t('institutions.democracy'), value: 'democracy' },
  { label: t('institutions.autocracy'), value: 'autocracy' },
  { label: t('institutions.anarchy'), value: 'anarchy' },
])

const sim = ref<Simulation | null>(null)
const busy = ref(false)
const error = ref('')
const canvasRef = ref<HTMLCanvasElement | null>(null)

const recentEvents = computed(() => (sim.value?.events ?? []).slice(-30).reverse())

const statusLabel = computed(() => {
  if (!sim.value) return ''
  const key = `status.${sim.value.status}` as const
  const translated = t(key)
  return translated === key ? sim.value.status : translated
})

const turnStatusLabel = computed(() => {
  if (!sim.value) return ''
  return t('turnStatus', { turn: sim.value.world.turn, status: statusLabel.value })
})

function actionLabel(action: string): string {
  const key = `actionTypes.${action}`
  const translated = t(key)
  return translated === key ? action : translated
}

async function onLocaleChange(code: string) {
  if (!code || code === locale.value) return
  await setLocale(code)
}

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
      <div class="header-left">
        <p class="eyebrow">{{ t('brand') }}</p>
        <h1>{{ t('consoleTitle') }}</h1>
      </div>
      <div class="header-right">
        <div class="lang" role="group" :aria-label="t('language')">
          <button
            type="button"
            class="lang-btn"
            :class="{ active: locale === 'ja' }"
            :aria-pressed="locale === 'ja'"
            @click="onLocaleChange('ja')"
          >
            JA
          </button>
          <span class="lang-sep" aria-hidden="true">/</span>
          <button
            type="button"
            class="lang-btn"
            :class="{ active: locale === 'en' }"
            :aria-pressed="locale === 'en'"
            @click="onLocaleChange('en')"
          >
            EN
          </button>
        </div>
        <div class="status-slot">
          <Tag v-if="sim" :value="turnStatusLabel" severity="info" />
        </div>
      </div>
    </header>

    <div class="grid">
      <aside class="panel sidebar">
        <h2>{{ t('initialConditions') }}</h2>
        <label>{{ t('population') }}</label>
        <InputNumber v-model="population" :min="2" :max="20" show-buttons class="field-control" />
        <label>{{ t('seed') }}</label>
        <InputNumber v-model="seed" show-buttons class="field-control" />
        <label>{{ t('taxRate') }}</label>
        <InputNumber v-model="taxRate" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
        <label>{{ t('education') }}</label>
        <InputNumber v-model="education" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
        <label>{{ t('institution') }}</label>
        <Dropdown v-model="institution" :options="institutionOptions" option-label="label" option-value="value" class="field-control" />

        <div class="actions">
          <Button :label="t('actions.create')" icon="pi pi-plus" class="action-btn" :loading="busy" @click="createSimulation" />
          <Button :label="t('actions.tick')" icon="pi pi-play" class="action-btn" :disabled="!sim" :loading="busy" severity="success" @click="tick(1)" />
          <Button :label="t('actions.tick5')" icon="pi pi-forward" class="action-btn" :disabled="!sim" :loading="busy" severity="help" @click="tick(5)" />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <div v-if="sim?.last_metrics" class="metrics">
          <h2>{{ t('metrics.title') }}</h2>
          <ul>
            <li>{{ t('metrics.inequality') }} {{ sim.last_metrics.inequality.toFixed(3) }}</li>
            <li>{{ t('metrics.trust') }} {{ sim.last_metrics.mean_trust.toFixed(3) }}</li>
            <li>{{ t('metrics.cooperationRate') }} {{ sim.last_metrics.cooperation_rate.toFixed(3) }}</li>
            <li>{{ t('metrics.authority') }} {{ sim.last_metrics.authority.toFixed(3) }}</li>
            <li>{{ t('metrics.happiness') }} {{ sim.last_metrics.mean_happiness.toFixed(3) }}</li>
          </ul>
        </div>
      </aside>

      <main class="viewport panel">
        <h2>{{ t('map.title') }}</h2>
        <canvas ref="canvasRef" width="720" height="520" class="map" />
      </main>

      <section class="panel events">
        <h2>{{ t('events.title') }}</h2>
        <DataTable :value="recentEvents" size="small" scrollable scroll-height="520px">
          <Column field="turn" :header="t('events.turn')" style="width: 4rem" />
          <Column field="actor_id" :header="t('events.actor')" />
          <Column :header="t('events.action')">
            <template #body="{ data }">
              {{ actionLabel(data.action) }}
            </template>
          </Column>
          <Column field="detail" :header="t('events.detail')" />
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) 168px;
  align-items: start;
  gap: 1rem;
  min-height: 4.5rem;
  margin-bottom: 1rem;
}

.header-left {
  min-width: 0;
}

.header-right {
  width: 168px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.45rem;
}

.lang {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  line-height: 1;
}

.lang-btn {
  margin: 0;
  padding: 0.1rem 0.15rem;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  opacity: 0.7;
}

.lang-btn:hover {
  opacity: 1;
  color: var(--text);
}

.lang-btn.active {
  color: var(--text);
  opacity: 1;
}

.lang-sep {
  color: var(--muted);
  font-size: 0.65rem;
  opacity: 0.5;
}

.status-slot {
  min-height: 1.6rem;
  max-width: 168px;
  display: flex;
  justify-content: flex-end;
}

.status-slot :deep(.p-tag) {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  line-height: 1.25;
  min-height: 1.875rem;
}

h2 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: var(--muted);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 340px;
  gap: 1rem;
  align-items: start;
}

.panel {
  background: color-mix(in srgb, var(--panel) 92%, transparent);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1rem;
  min-width: 0;
}

.sidebar {
  overflow: hidden;
}

label {
  display: block;
  margin: 0.7rem 0 0.25rem;
  color: var(--muted);
  font-size: 0.8rem;
}

.field-control {
  width: 100%;
  max-width: 100%;
}

.sidebar :deep(.p-inputnumber),
.sidebar :deep(.p-dropdown) {
  width: 100%;
  max-width: 100%;
  display: inline-flex;
  align-items: stretch;
  height: 2.5rem;
}

.sidebar :deep(.p-inputnumber-input) {
  min-width: 0;
  flex: 1 1 auto;
  height: 100%;
  box-sizing: border-box;
}

.sidebar :deep(.p-dropdown) {
  min-width: 0;
  flex: 1 1 auto;
}

.sidebar :deep(.p-dropdown .p-dropdown-label),
.sidebar :deep(.p-dropdown .p-dropdown-trigger) {
  display: flex;
  align-items: center;
}

.sidebar :deep(.p-inputnumber-button-group) {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-self: stretch;
  height: 100%;
}

.sidebar :deep(.p-inputnumber-button) {
  flex: 1 1 0;
  width: 2rem;
  margin: 0;
  padding: 0;
  height: auto !important;
  min-height: 0;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.action-btn {
  width: 100%;
}

.action-btn :deep(.p-button-label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

  .header {
    grid-template-columns: minmax(0, 1fr) auto;
  }
}
</style>
