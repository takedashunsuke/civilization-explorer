<script setup lang="ts">
import type { HistoryPoint } from '~/utils/experimentWorlds'

const props = defineProps<{
  history: HistoryPoint[]
  title?: string
}>()

const { t } = useI18n()

const W = 280
const H = 72
const PAD = { top: 8, right: 8, bottom: 14, left: 8 }

type Pt = { x: number; y: number; turn: number }

function series(
  key: 'population_alive' | 'resource_pool',
): { line: string; points: Pt[]; disasters: number[] } {
  const rows = props.history.filter((h) => typeof h.turn === 'number')
  if (rows.length < 2) return { line: '', points: [], disasters: [] }

  const values = rows.map((h) => Number(h[key] ?? 0))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const turns = rows.map((h) => h.turn)
  const t0 = turns[0]
  const t1 = turns[turns.length - 1]
  const tSpan = t1 - t0 || 1
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom

  const points: Pt[] = rows.map((h, i) => {
    const x = PAD.left + ((h.turn - t0) / tSpan) * innerW
    const y = PAD.top + innerH - ((values[i] - min) / span) * innerH
    return { x, y, turn: h.turn }
  })
  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
  const disasters = rows.filter((h) => (h.disaster_events ?? 0) > 0).map((h) => h.turn)
  return { line, points, disasters }
}

const pop = computed(() => series('population_alive'))
const res = computed(() => series('resource_pool'))

const disasterXs = computed(() => {
  const rows = props.history.filter((h) => typeof h.turn === 'number')
  if (rows.length < 2) return [] as number[]
  const turns = rows.map((h) => h.turn)
  const t0 = turns[0]
  const t1 = turns[turns.length - 1]
  const tSpan = t1 - t0 || 1
  const innerW = W - PAD.left - PAD.right
  return [...new Set(pop.value.disasters)].map((turn) => PAD.left + ((turn - t0) / tSpan) * innerW)
})

const hasCurve = computed(() => pop.value.points.length >= 2)
</script>

<template>
  <section class="recovery-curve" :aria-label="title || t('experiment.recoveryTitle')">
    <p class="recovery-title">{{ title || t('experiment.recoveryTitle') }}</p>
    <p v-if="!hasCurve" class="recovery-empty">{{ t('experiment.recoveryEmpty') }}</p>
    <svg
      v-else
      class="recovery-svg"
      :viewBox="`0 0 ${W} ${H}`"
      role="img"
      :aria-label="t('experiment.recoveryTitle')"
    >
      <line
        v-for="(x, i) in disasterXs"
        :key="`d-${i}`"
        :x1="x"
        :x2="x"
        :y1="PAD.top"
        :y2="H - PAD.bottom"
        class="recovery-disaster"
      />
      <path :d="pop.line" class="recovery-pop" fill="none" />
      <path :d="res.line" class="recovery-res" fill="none" />
    </svg>
    <ul v-if="hasCurve" class="recovery-legend">
      <li><span class="swatch pop" />{{ t('experiment.recoveryPop') }}</li>
      <li><span class="swatch res" />{{ t('experiment.recoveryRes') }}</li>
      <li><span class="swatch disaster" />{{ t('experiment.recoveryDisaster') }}</li>
    </ul>
  </section>
</template>

<style scoped>
.recovery-curve {
  margin: 0.45rem 0 0.35rem;
}

.recovery-title {
  margin: 0 0 0.25rem;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--muted, #9aa7b5);
}

.recovery-empty {
  margin: 0;
  font-size: 0.65rem;
  color: var(--muted, #9aa7b5);
}

.recovery-svg {
  display: block;
  width: 100%;
  height: auto;
  max-height: 4.5rem;
  border: 1px solid var(--line, #314050);
  border-radius: 4px;
  background: color-mix(in srgb, var(--panel, #1c252f) 88%, #000);
}

.recovery-pop {
  stroke: #7ec8e3;
  stroke-width: 1.6;
}

.recovery-res {
  stroke: #c4a35a;
  stroke-width: 1.4;
  stroke-dasharray: 3 2;
}

.recovery-disaster {
  stroke: rgba(220, 90, 90, 0.45);
  stroke-width: 1;
}

.recovery-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem 0.75rem;
  margin: 0.2rem 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.6rem;
  color: var(--muted, #9aa7b5);
}

.swatch {
  display: inline-block;
  width: 0.7rem;
  height: 0.18rem;
  margin-right: 0.25rem;
  vertical-align: middle;
  border-radius: 1px;
}

.swatch.pop {
  background: #7ec8e3;
}

.swatch.res {
  background: #c4a35a;
}

.swatch.disaster {
  width: 0.12rem;
  height: 0.55rem;
  background: rgba(220, 90, 90, 0.7);
}
</style>
