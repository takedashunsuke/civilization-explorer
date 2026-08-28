export const EXPERIMENT_SEED = 42

export type ExperimentVariantId = 'peace' | 'famine' | 'war' | 'trade'

export const EXPERIMENT_VARIANT_IDS: ExperimentVariantId[] = [
  'peace',
  'famine',
  'war',
  'trade',
]

export type ExperimentSummary = {
  variant?: string
  variant_label_ja?: string
  seed?: number
  turn?: number
  calendar_year?: number
  population_alive?: number
  population_delta_pct?: number
  resource_pool?: number
  trade_openness_mean?: number
  conflicts_total?: number
  cooperations_total?: number
  regime_shifts?: number
  disasters?: number
  dominant_archetype?: string
  archetypes?: string[]
  trajectories?: string[]
  institutions?: string[]
  spotlight_agent_id?: string | null
  spotlight_role?: string | null
}

export type ExperimentDesign = {
  seed: number
  population_per_region: number
  total_agents: number
  fixed: string[]
  varied: string[]
  variants: Array<{
    id: ExperimentVariantId
    label_ja: string
    env: Record<string, number | string>
  }>
}
