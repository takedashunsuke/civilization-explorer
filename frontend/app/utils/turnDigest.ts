import { polityKind } from '~/utils/groupColors'
import { macroOf } from '~/utils/continents'

export type DigestEvent = {
  turn: number
  actor_id: string
  action: string
  target_id?: string | null
  detail_key?: string
  success?: boolean | null
  extra?: Record<string, string>
}

export type DigestAgent = {
  alive: boolean
  region_id?: string | null
  settlement_id?: string | null
  traits?: string[]
}

export type DigestSettlement = {
  member_ids: string[]
  region_id?: string | null
}

export type DigestRegion = {
  id: string
  subregion_id?: string | null
  institution?: string
  tax_rate?: number
  education_level?: number
}

export type DigestSim = {
  world: {
    turn: number
    regions?: DigestRegion[]
  }
  agents: DigestAgent[]
  settlements?: DigestSettlement[]
  events: DigestEvent[]
}

export type RegionObservation = {
  regionId: string
  subregionId: string | null
  population: number
  bands: number
  cities: number
  nations: number
  conflicts: number
  cooperations: number
  births: number
  deaths: number
  disasters: number
  regimeShifts: number
}

export type NotableEventRef = {
  key: string
  actorId: string
  targetId?: string | null
  extra?: Record<string, string>
}

export type TurnDigestData = {
  turn: number
  totals: {
    population: number
    groups: number
    cities: number
    nations: number
    lone: number
    conflicts: number
    cooperations: number
    births: number
    deaths: number
    disasters: number
    regimeShifts: number
  }
  cumulative: {
    conflicts: number
    cooperations: number
    births: number
    deaths: number
    disasters: number
    regimeShifts: number
  }
  regionObservations: RegionObservation[]
  notableEvents: NotableEventRef[]
}

const HEADLINE_KEYS = new Set([
  'historic_quake',
  'disaster_earthquake',
  'disaster_typhoon',
  'epidemic',
  'regime_shift',
  'group_conflict_out',
  'group_conflict_in',
  'disaster_flood',
  'weather_storm',
  'disaster_heatwave',
  'weather_heat',
  'disaster_frost',
  'weather_blizzard',
  'weather_drought',
])

export function inferDetailKey(row: DigestEvent): string {
  if (row.detail_key) return row.detail_key
  if (row.action === 'cooperate') return row.success ? 'cooperate_success' : 'cooperate_failed'
  if (row.action === 'conflict') return row.success ? 'conflict_win' : 'conflict_lose'
  if (row.action === 'migrate') return 'migrate'
  if (row.action === 'obey') return 'obey'
  if (row.action === 'resist') return 'resist'
  if (row.action === 'birth') return 'birth'
  if (row.action === 'death') return 'death'
  if (row.action === 'lead') return row.target_id ? 'lead_takeover' : 'lead_new'
  if (row.action === 'trait') return row.success ? 'trait_gain_charisma' : 'trait_lose_charisma'
  return 'wait'
}

function eventRegionId(event: DigestEvent, agentsById: Map<string, DigestAgent>): string | null {
  const macro = macroOf(event.actor_id)
  if (macro) return macro
  if (event.actor_id.startsWith('s')) {
    return agentsById.get(event.actor_id)?.region_id ?? null
  }
  const actor = agentsById.get(event.actor_id)
  return actor?.region_id ?? null
}

function countPolities(settlements: DigestSettlement[], regionId: string) {
  let bands = 0
  let cities = 0
  let nations = 0
  for (const settlement of settlements) {
    if (settlement.region_id !== regionId) continue
    const n = settlement.member_ids.length
    if (n < 2) continue
    const kind = polityKind(n)
    if (kind === 'nation') nations += 1
    else if (kind === 'city') cities += 1
    else bands += 1
  }
  return { bands, cities, nations }
}

function countTurnActions(events: DigestEvent[], turn: number) {
  const turnEvents = events.filter((e) => e.turn === turn)
  return {
    conflicts: turnEvents.filter((e) => e.action === 'conflict').length,
    cooperations: turnEvents.filter((e) => e.action === 'cooperate').length,
    births: turnEvents.filter((e) => e.action === 'birth').length,
    deaths: turnEvents.filter((e) => e.action === 'death').length,
    disasters: turnEvents.filter((e) => e.action === 'disaster').length,
    regimeShifts: turnEvents.filter((e) => e.action === 'regime' || inferDetailKey(e) === 'regime_shift').length,
  }
}

function countCumulative(events: DigestEvent[]) {
  return {
    conflicts: events.filter((e) => e.action === 'conflict').length,
    cooperations: events.filter((e) => e.action === 'cooperate').length,
    births: events.filter((e) => e.action === 'birth').length,
    deaths: events.filter((e) => e.action === 'death').length,
    disasters: events.filter((e) => e.action === 'disaster').length,
    regimeShifts: events.filter((e) => e.action === 'regime' || inferDetailKey(e) === 'regime_shift').length,
  }
}

function pickNotableEvents(events: DigestEvent[], turn: number): NotableEventRef[] {
  const turnEvents = events.filter((e) => e.turn === turn)
  const picked: NotableEventRef[] = []
  const seen = new Set<string>()
  for (const row of turnEvents) {
    const key = inferDetailKey(row)
    const isHeadline = HEADLINE_KEYS.has(key) || row.action === 'regime' || row.action === 'disaster'
    if (!isHeadline) continue
    const dedupe = `${key}:${row.actor_id}:${row.target_id ?? ''}`
    if (seen.has(dedupe)) continue
    seen.add(dedupe)
    picked.push({
      key,
      actorId: row.actor_id,
      targetId: row.target_id,
      extra: row.extra,
    })
  }
  return picked.slice(0, 6)
}

export function buildTurnDigest(sim: DigestSim | null): TurnDigestData | null {
  if (!sim) return null

  const turn = sim.world.turn
  const agents = sim.agents.filter((a) => a.alive)
  const settlements = sim.settlements ?? []
  const agentsById = new Map(sim.agents.map((a) => [a.id, a]))
  const turnActions = countTurnActions(sim.events, turn)
  const cumulative = countCumulative(sim.events)

  let groups = 0
  let cities = 0
  let nations = 0
  for (const settlement of settlements) {
    const n = settlement.member_ids.length
    if (n < 2) continue
    const kind = polityKind(n)
    if (kind === 'nation') nations += 1
    else if (kind === 'city') cities += 1
    else groups += 1
  }

  const lone = agents.filter((a) => !a.settlement_id).length
  const regionIds =
    sim.world.regions?.map((r) => r.id) ??
    [...new Set(agents.map((a) => a.region_id).filter(Boolean) as string[])]

  const regionObservations: RegionObservation[] = regionIds.map((regionId) => {
    const regionMeta = sim.world.regions?.find((r) => r.id === regionId)
    const population = agents.filter((a) => a.region_id === regionId).length
    const polities = countPolities(settlements, regionId)
    const turnEvents = sim.events.filter((e) => e.turn === turn && eventRegionId(e, agentsById) === regionId)
    return {
      regionId,
      subregionId: regionMeta?.subregion_id ?? null,
      population,
      ...polities,
      conflicts: turnEvents.filter((e) => e.action === 'conflict').length,
      cooperations: turnEvents.filter((e) => e.action === 'cooperate').length,
      births: turnEvents.filter((e) => e.action === 'birth').length,
      deaths: turnEvents.filter((e) => e.action === 'death').length,
      disasters: turnEvents.filter((e) => e.action === 'disaster').length,
      regimeShifts: turnEvents.filter((e) => e.action === 'regime' || inferDetailKey(e) === 'regime_shift').length,
    }
  })

  return {
    turn,
    totals: {
      population: agents.length,
      groups,
      cities,
      nations,
      lone,
      ...turnActions,
    },
    cumulative,
    regionObservations,
    notableEvents: pickNotableEvents(sim.events, turn),
  }
}
