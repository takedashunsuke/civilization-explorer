<script setup lang="ts">
import { Chart, Filler, Legend, LineElement, PointElement, RadarController, RadialLinearScale, Tooltip } from 'chart.js'
import { hexRgba, settlementColor } from '~/utils/groupColors'

Chart.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

type Dataset = {
  id: string
  label: string
  values: number[]
}

const props = defineProps<{
  labels: string[]
  datasets: Dataset[]
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null

function palette(id: string): string {
  return settlementColor(id)
}

function buildData() {
  return {
    labels: props.labels,
    datasets: props.datasets.map((ds) => {
      const color = palette(ds.id)
      return {
        label: ds.label,
        data: ds.values,
        borderColor: color,
        backgroundColor: hexRgba(color, 0.18),
        pointBackgroundColor: color,
        pointBorderColor: '#1a222c',
        borderWidth: 2,
        pointRadius: 3,
      }
    }),
  }
}

function render() {
  if (!canvas.value) return
  const data = buildData()
  if (chart) {
    chart.data = data
    chart.update()
    chart.resize()
    return
  }
  chart = new Chart(canvas.value, {
    type: 'radar',
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 280 },
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#f7fafc', boxWidth: 10, font: { size: 11 } },
        },
        tooltip: {
          callbacks: {
            label(ctx) {
              const v = typeof ctx.parsed === 'object' && ctx.parsed && 'r' in ctx.parsed
                ? Number(ctx.parsed.r)
                : Number(ctx.raw)
              return ` ${ctx.dataset.label}: ${v.toFixed(2)}`
            },
          },
        },
      },
      scales: {
        r: {
          min: 0,
          max: 1,
          ticks: { display: false, count: 5 },
          grid: { color: 'rgba(247, 250, 252, 0.14)' },
          angleLines: { color: 'rgba(247, 250, 252, 0.14)' },
          pointLabels: { color: '#f7fafc', font: { size: 11 } },
        },
      },
    },
  })
}

onMounted(render)
watch(() => [props.labels, props.datasets], render, { deep: true })
onBeforeUnmount(() => {
  chart?.destroy()
  chart = null
})
</script>

<template>
  <div class="radar-wrap">
    <canvas ref="canvas" />
  </div>
</template>

<style scoped>
.radar-wrap {
  height: 13.5rem;
  min-width: 0;
}
</style>
