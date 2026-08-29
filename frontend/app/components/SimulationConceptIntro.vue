<script setup lang="ts">
defineProps<{
  compact?: boolean
}>()
</script>

<template>
  <div class="sim-concept-intro" :class="{ 'sim-concept-intro--compact': compact }">
    <p class="sim-concept-question">{{ $t('concept.question') }}</p>
    <p class="sim-concept-summary">{{ $t('concept.summary') }}</p>
    <section class="sim-concept-structure" :aria-label="$t('concept.structureTitle')">
      <h3>{{ $t('concept.structureTitle') }}</h3>
      <div class="sim-concept-structure-rows">
        <p class="sim-concept-structure-row">
          <span class="sim-concept-structure-k">{{ $t('concept.structureWorldsLabel') }}</span>
          <span>{{ $t('concept.structureWorldsBody') }}</span>
        </p>
        <p class="sim-concept-structure-row sim-concept-structure-row--nested">
          <span class="sim-concept-structure-k">{{ $t('concept.structureApplyLabel') }}</span>
          <span>{{ $t('concept.structureApplyBody') }}</span>
        </p>
        <p class="sim-concept-structure-row sim-concept-structure-row--nested sim-concept-structure-row--emerges">
          <span class="sim-concept-structure-k">{{ $t('concept.structureEmergesLabel') }}</span>
          <span>{{ $t('concept.structureEmergesBody') }}</span>
        </p>
        <p class="sim-concept-structure-row sim-concept-structure-row--nested">
          <span class="sim-concept-structure-k">{{ $t('concept.structureMapLabel') }}</span>
          <span>{{ $t('concept.structureMapBody') }}</span>
        </p>
      </div>
      <p class="sim-concept-structure-note">{{ $t('concept.structureCustomHint') }}</p>
    </section>
    <section class="sim-concept-section">
      <h3>{{ $t('concept.experienceTitle') }}</h3>
      <ul class="sim-concept-list">
        <li>
          <strong>{{ $t('concept.experienceIfLabel') }}</strong>
          {{ $t('concept.experienceIfBody') }}
        </li>
        <li>
          <strong>{{ $t('concept.experienceAutonomyLabel') }}</strong>
          {{ $t('concept.experienceAutonomyBody') }}
        </li>
      </ul>
    </section>
    <section class="sim-concept-section">
      <h3>{{ $t('concept.howTitle') }}</h3>
      <ol class="sim-concept-steps">
        <li>
          <strong>{{ $t('concept.howStep1Label') }}</strong>
          {{ $t('concept.howStep1Body') }}
        </li>
        <li>
          <strong>{{ $t('concept.howStep2Label') }}</strong>
          {{ $t('concept.howStep2Body') }}
        </li>
        <li>
          <strong>{{ $t('concept.howStep3Label') }}</strong>
          {{ $t('concept.howStep3Body') }}
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.sim-concept-intro {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sim-concept-intro--compact {
  gap: 0.55rem;
  margin-bottom: 0.65rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 88%, #243040);
}

.sim-concept-question {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 650;
  line-height: 1.35;
  color: color-mix(in srgb, var(--accent) 55%, var(--text));
}

.sim-concept-intro--compact .sim-concept-question {
  font-size: 0.88rem;
}

.sim-concept-summary {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--text);
}

.sim-concept-intro--compact .sim-concept-summary {
  font-size: 0.78rem;
}

.sim-concept-structure {
  padding: 0.55rem 0.65rem;
  border: 1px solid color-mix(in srgb, var(--accent) 28%, var(--line));
  border-radius: 8px;
  background: color-mix(in srgb, var(--accent) 6%, var(--panel));
}

.sim-concept-intro--compact .sim-concept-structure {
  padding: 0.45rem 0.55rem;
}

.sim-concept-structure h3 {
  margin: 0 0 0.35rem;
  font-size: 0.72rem;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}

.sim-concept-structure-rows {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.sim-concept-structure-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.45rem;
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--text);
}

.sim-concept-intro--compact .sim-concept-structure-row {
  font-size: 0.74rem;
}

.sim-concept-structure-row--nested {
  padding-left: 0.85rem;
  border-left: 2px solid color-mix(in srgb, var(--accent) 35%, var(--line));
}

.sim-concept-structure-row--emerges {
  border-left-color: color-mix(in srgb, #7ec87a 45%, var(--line));
}

.sim-concept-structure-row--emerges .sim-concept-structure-k {
  color: color-mix(in srgb, #7ec87a 55%, var(--text));
}

.sim-concept-structure-note {
  margin: 0.4rem 0 0;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--muted);
}

.sim-concept-intro--compact .sim-concept-structure-note {
  font-size: 0.68rem;
}

.sim-concept-structure-k {
  flex: 0 0 auto;
  font-weight: 650;
  color: color-mix(in srgb, var(--accent) 50%, var(--text));
}

.sim-concept-section h3 {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}

.sim-concept-intro--compact .sim-concept-section h3 {
  font-size: 0.72rem;
  margin-bottom: 0.28rem;
}

.sim-concept-list,
.sim-concept-steps {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--text);
}

.sim-concept-intro--compact .sim-concept-list,
.sim-concept-intro--compact .sim-concept-steps {
  font-size: 0.76rem;
  line-height: 1.45;
}

.sim-concept-list li + li,
.sim-concept-steps li + li {
  margin-top: 0.3rem;
}

.sim-concept-intro--compact .sim-concept-list li + li,
.sim-concept-intro--compact .sim-concept-steps li + li {
  margin-top: 0.2rem;
}

.sim-concept-list strong,
.sim-concept-steps strong {
  font-weight: 650;
}
</style>
