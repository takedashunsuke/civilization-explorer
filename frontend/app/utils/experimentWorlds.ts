export const EXPERIMENT_SEED = 42

export type ExperimentProtocol = 'environment' | 'resilience'

export type EnvironmentVariantId = 'lush' | 'lean' | 'volatile' | 'balanced'
export type ResilienceVariantId = 'civic' | 'autocrat' | 'commune' | 'fracture'
export type ExperimentVariantId = EnvironmentVariantId | ResilienceVariantId

export const ENVIRONMENT_VARIANT_IDS: EnvironmentVariantId[] = [
  'lush',
  'lean',
  'volatile',
  'balanced',
]

export const RESILIENCE_VARIANT_IDS: ResilienceVariantId[] = [
  'civic',
  'autocrat',
  'commune',
  'fracture',
]

/** @deprecated Prefer ENVIRONMENT_VARIANT_IDS or variantIdsForProtocol() */
export const EXPERIMENT_VARIANT_IDS: ExperimentVariantId[] = [...ENVIRONMENT_VARIANT_IDS]

export function isEnvironmentVariant(id: string): id is EnvironmentVariantId {
  return (ENVIRONMENT_VARIANT_IDS as string[]).includes(id)
}

export function isResilienceVariant(id: string): id is ResilienceVariantId {
  return (RESILIENCE_VARIANT_IDS as string[]).includes(id)
}

export function protocolForVariant(id: string): ExperimentProtocol {
  if (isResilienceVariant(id)) return 'resilience'
  return 'environment'
}

export function variantIdsForProtocol(protocol: ExperimentProtocol): ExperimentVariantId[] {
  return protocol === 'resilience' ? [...RESILIENCE_VARIANT_IDS] : [...ENVIRONMENT_VARIANT_IDS]
}

export function defaultVariantForProtocol(protocol: ExperimentProtocol): ExperimentVariantId {
  return protocol === 'resilience' ? 'civic' : 'balanced'
}

export type HistoryPoint = {
  turn: number
  summary?: string
  population_alive?: number | null
  resource_pool?: number | null
  mean_authority?: number | null
  disaster_events?: number
}

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
  pop_retention_ratio?: number | null
  pop_recovery_ratio?: number | null
  resilience_label?: string | null
  coop_vs_conflict_post_shock?: number | null
  regime_break?: boolean | null
  shock_count?: number | null
  disaster_deaths?: number | null
}

export type ExperimentDesign = {
  seed: number
  population_per_region: number
  total_agents: number
  fixed: string[]
  varied: string[]
  emerges_in_play?: string[]
  variants: Array<{
    id: ExperimentVariantId
    label_ja: string
    env?: Record<string, number | string>
    social?: Record<string, number | string>
  }>
}
