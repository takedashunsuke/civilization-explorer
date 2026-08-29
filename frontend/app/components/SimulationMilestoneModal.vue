<script setup lang="ts">
import Button from 'primevue/button'

export type MilestoneSnapshot = {
  yearLabel: string
  japanEra: string
  worldEra: string
  turn: number
  headline: string
  summary: string
  population: number
  populationDelta: number
  settlements: number
  conflicts: number
  cooperations: number
  inequality?: number
  trust?: number
  happiness?: number
  dominantArchetype?: string
}

defineProps<{
  open: boolean
  snapshot: MilestoneSnapshot | null
  busy?: boolean
}>()

const emit = defineEmits<{
  continue: []
  changeConditions: []
}>()

const { t } = useI18n()

function pct(value: number | undefined): string {
  if (value == null) return '—'
  return `${Math.round(value * 100)}%`
}

function deltaLabel(delta: number): string {
  if (delta > 0) return `+${delta}`
  return String(delta)
}
</script>

<template>
  <template v-if="open && snapshot">
    <div class="modal-backdrop milestone-backdrop" aria-hidden="true" />
    <aside
      class="milestone-modal panel"
      role="dialog"
      aria-modal="true"
      :aria-label="t('milestone.title')"
    >
      <div class="panel-heading events-heading">
        <div>
          <p class="milestone-eyebrow">{{ t('milestone.title') }}</p>
          <h2>{{ snapshot.yearLabel }}</h2>
          <p class="milestone-subtitle">
            {{ t('milestone.subtitle', { turn: snapshot.turn }) }}
            · {{ snapshot.japanEra }}
            · {{ snapshot.worldEra }}
          </p>
        </div>
      </div>

      <div class="milestone-body">
        <p v-if="snapshot.headline" class="milestone-headline">{{ snapshot.headline }}</p>
        <p v-if="snapshot.summary" class="milestone-summary">{{ snapshot.summary }}</p>

        <section class="milestone-section" :aria-label="t('milestone.statsTitle')">
          <h3>{{ t('milestone.statsTitle') }}</h3>
          <ul class="milestone-stats">
            <li>
              {{ t('milestone.population', { alive: snapshot.population, delta: deltaLabel(snapshot.populationDelta) }) }}
            </li>
            <li>{{ t('milestone.settlements', { count: snapshot.settlements }) }}</li>
            <li>{{ t('milestone.conflicts', { count: snapshot.conflicts }) }}</li>
            <li>{{ t('milestone.cooperations', { count: snapshot.cooperations }) }}</li>
          </ul>
        </section>

        <section
          v-if="snapshot.inequality != null || snapshot.trust != null || snapshot.happiness != null"
          class="milestone-section"
          :aria-label="t('milestone.metricsTitle')"
        >
          <h3>{{ t('milestone.metricsTitle') }}</h3>
          <ul class="milestone-metrics">
            <li v-if="snapshot.inequality != null">
              {{ t('milestone.inequality') }} {{ pct(snapshot.inequality) }}
            </li>
            <li v-if="snapshot.trust != null">
              {{ t('milestone.trust') }} {{ pct(snapshot.trust) }}
            </li>
            <li v-if="snapshot.happiness != null">
              {{ t('milestone.happiness') }} {{ pct(snapshot.happiness) }}
            </li>
          </ul>
        </section>

        <p v-if="snapshot.dominantArchetype" class="milestone-archetype">
          {{ t('milestone.dominantArchetype') }}: {{ snapshot.dominantArchetype }}
        </p>
      </div>

      <footer class="milestone-actions">
        <p class="milestone-change-hint">{{ t('milestone.changeHint') }}</p>
        <div class="milestone-buttons">
          <Button
            :label="t('milestone.continue')"
            icon="pi pi-play"
            class="milestone-btn"
            :disabled="busy"
            @click="emit('continue')"
          />
          <Button
            :label="t('milestone.changeConditions')"
            icon="pi pi-sliders-h"
            class="milestone-btn"
            severity="secondary"
            :disabled="busy"
            @click="emit('changeConditions')"
          />
        </div>
      </footer>
    </aside>
  </template>
</template>

<style scoped>
.milestone-backdrop {
  z-index: 48;
}

.milestone-modal {
  position: fixed;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 50;
  width: min(36rem, calc(100vw - 1.5rem));
  max-height: calc(100dvh - 2rem);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0.7rem 0.85rem 0.75rem;
  background: #1c252f;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45);
}

.milestone-eyebrow {
  margin: 0 0 0.15rem;
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}

.milestone-subtitle {
  margin: 0.2rem 0 0;
  font-size: 0.72rem;
  color: var(--muted);
}

.milestone-body {
  overflow-y: auto;
  min-height: 0;
  flex: 1 1 auto;
  padding: 0.35rem 0.1rem 0.5rem;
}

.milestone-headline {
  margin: 0 0 0.45rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #e8eef4;
}

.milestone-summary {
  margin: 0 0 0.75rem;
  font-size: 0.82rem;
  line-height: 1.45;
  color: #c5d0dc;
}

.milestone-section {
  margin-bottom: 0.65rem;
}

.milestone-section h3 {
  margin: 0 0 0.35rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.milestone-stats,
.milestone-metrics {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.35rem 0.75rem;
  font-size: 0.8rem;
}

.milestone-archetype {
  margin: 0;
  font-size: 0.78rem;
  color: #aebccb;
}

.milestone-actions {
  flex-shrink: 0;
  padding-top: 0.35rem;
  border-top: 1px solid var(--line);
}

.milestone-change-hint {
  margin: 0 0 0.55rem;
  font-size: 0.68rem;
  color: var(--muted);
  line-height: 1.35;
}

.milestone-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.milestone-btn :deep(.p-button) {
  font-size: 0.82rem;
}
</style>
