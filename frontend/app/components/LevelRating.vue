<script setup lang="ts">
import Rating from 'primevue/rating'

const props = defineProps<{
  modelValue: number
  steps: number[]
  labels: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

function starsFromValue(value: number): number {
  let best = 0
  let bestDist = Number.POSITIVE_INFINITY
  for (let i = 0; i < props.steps.length; i++) {
    const dist = Math.abs(props.steps[i] - value)
    if (dist < bestDist || (dist === bestDist && i > best)) {
      bestDist = dist
      best = i
    }
  }
  return best + 1
}

const stars = computed({
  get: () => starsFromValue(props.modelValue),
  set: (next: number | null) => {
    const index = Math.min(Math.max(next ?? 1, 1), props.steps.length) - 1
    emit('update:modelValue', props.steps[index])
  },
})

const currentLabel = computed(() => props.labels[stars.value - 1] ?? '')
</script>

<template>
  <div class="level-rating">
    <Rating v-model="stars" :stars="steps.length" :cancel="false" :aria-label="currentLabel" />
    <span class="level-rating-label">{{ currentLabel }}</span>
  </div>
</template>

<style scoped>
.level-rating {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.12rem;
  width: 100%;
}

.level-rating-label {
  font-size: 0.7rem;
  line-height: 1.2;
  color: #d5e4f2;
}

.level-rating :deep(.p-rating) {
  gap: 0.08rem;
}

.level-rating :deep(.p-rating-icon) {
  font-size: 1.05rem;
  color: #4d6f8c;
}

.level-rating :deep(.p-rating-icon.p-rating-icon-active),
.level-rating :deep(.p-rating .p-rating-item.p-focus .p-rating-icon),
.level-rating :deep(.pi-star-fill) {
  color: #7ec4ff;
}
</style>
