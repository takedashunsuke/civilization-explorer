import type { MilestoneSnapshot } from '~/components/SimulationMilestoneModal.vue'
import type { ExperimentSummary } from '~/utils/experimentWorlds'

export type MilestoneExportEvent = {
  turn: number
  actor_id: string
  action: string
  target_id?: string | null
  detail: string
  detail_key?: string
  success?: boolean | null
  deltas?: Record<string, number>
  extra?: Record<string, string>
  alert?: string | null
}

export type MilestoneExportSim = {
  id: string
  controlled_experiment?: boolean
  experiment_variant?: string
  experiment_seed?: number
  experiment_summary?: ExperimentSummary
  world: {
    turn: number
    seed: number
    start_year: number
    years_per_turn?: number
    resource_pool?: number
    disaster_frequency?: number
    institution?: string
    tax_rate?: number
    regions?: Array<{
      id: string
      subregion_id?: string | null
      institution?: string
      tax_rate?: number
      resource_pool?: number
      disaster_frequency?: number
      trade_openness?: number
    }>
  }
  agents: Array<{
    id: string
    name: string
    alive: boolean
    wealth: number
    happiness: number
    settlement_id: string | null
    region_id?: string | null
    subregion_id?: string | null
    traits?: string[]
    personality?: { cooperation: number; aggression: number; ambition: number }
    age?: number
  }>
  settlements?: Array<{
    id: string
    member_ids: string[]
    leader_id?: string | null
    region_id?: string | null
    subregion_id?: string | null
    shared_wealth?: number
  }>
  events: MilestoneExportEvent[]
  region_readings?: Array<{
    region_id: string
    subregion_id?: string | null
    tension: number
    prosperity: number
    discontent: number
    cohesion: number
    rising_archetype: string
    trajectory: string
    summary: string
    source?: string
  }>
  region_policies?: Array<{
    region_id: string
    subregion_id?: string | null
    action: string
    intensity: number
    reason: string
    source?: string
  }>
  world_summary?: string
  last_metrics?: {
    inequality?: number
    mean_trust?: number
    mean_happiness?: number
    cooperation_rate?: number
    authority?: number
    reading_source?: string
    world_summary?: string
  } | null
}

export type MilestoneExportFormatters = {
  formatYearLabel: (year: number) => string
  actionLabel: (action: string) => string
  actorLabel: (id: string) => string
  eventDetail: (row: MilestoneExportEvent) => string
  isHeadlineEvent: (row: MilestoneExportEvent) => boolean
  headlineText: (row: MilestoneExportEvent) => string
  archetypeLabel: (key: string) => string
  trajectoryLabel: (key: string) => string
  regionLabel: (id: string) => string
  institutionLabel: (key: string) => string
  variantLabel?: (variant: string) => string
}

function line(title: string, body?: string | number | null): string {
  if (body == null || body === '') return `${title}: —`
  return `${title}: ${body}`
}

function section(title: string): string {
  return `\n${'='.repeat(72)}\n${title}\n${'='.repeat(72)}\n`
}

function subsection(title: string): string {
  return `\n--- ${title} ---\n`
}

function pct(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${Math.round(value * 100)}%`
}

function calendarYearForTurn(sim: MilestoneExportSim, turn: number): number {
  const start = sim.world.start_year ?? 1000
  const ypt = sim.world.years_per_turn ?? 10
  return start + turn * ypt
}

function countByAction(events: MilestoneExportEvent[]): Record<string, number> {
  const out: Record<string, number> = {}
  for (const e of events) {
    out[e.action] = (out[e.action] ?? 0) + 1
  }
  return out
}

export function buildMilestoneExportText(
  sim: MilestoneExportSim,
  milestoneYear: number,
  snapshot: MilestoneSnapshot,
  formatters: MilestoneExportFormatters,
): string {
  const lines: string[] = []
  const turn = sim.world.turn
  const ypt = sim.world.years_per_turn ?? 10
  const alive = sim.agents.filter((a) => a.alive)
  const events = [...sim.events].sort((a, b) => a.turn - b.turn || a.actor_id.localeCompare(b.actor_id))
  const actionCounts = countByAction(events)

  lines.push('Civilization Explorer — マイルストーン・レポート')
  lines.push(`生成: ${new Date().toISOString()}`)
  lines.push(line('シミュレーション ID', sim.id))
  lines.push(line('シード', sim.world.seed))
  if (sim.controlled_experiment) {
    const variant = sim.experiment_variant || '—'
    lines.push(line('対照実験', 'yes'))
    lines.push(line('環境パターン', formatters.variantLabel?.(variant) ?? variant))
    lines.push(line('実験シード', sim.experiment_seed ?? sim.world.seed))
  }

  lines.push(section('節目'))
  lines.push(line('暦年', snapshot.yearLabel))
  lines.push(line('日本史', snapshot.japanEra))
  lines.push(line('世界史', snapshot.worldEra))
  lines.push(line('ターン', `${turn}（1ターン=${ypt}年）`))
  lines.push(line('節目の年', milestoneYear))

  lines.push(section('要約（この節目）'))
  if (snapshot.headline) lines.push(line('見出し', snapshot.headline))
  if (snapshot.summary) lines.push(snapshot.summary)

  lines.push(section('累計指標'))
  lines.push(line('生存人口', `${snapshot.population}（${snapshot.populationDelta >= 0 ? '+' : ''}${snapshot.populationDelta}）`))
  lines.push(line('集落数', snapshot.settlements))
  lines.push(line('争い（累計）', snapshot.conflicts))
  lines.push(line('共同（累計）', snapshot.cooperations))
  if (snapshot.dominantArchetype) lines.push(line('台頭する型', snapshot.dominantArchetype))
  if (snapshot.inequality != null) lines.push(line('不平等', pct(snapshot.inequality)))
  if (snapshot.trust != null) lines.push(line('信頼', pct(snapshot.trust)))
  if (snapshot.happiness != null) lines.push(line('幸福', pct(snapshot.happiness)))

  const es = sim.experiment_summary
  if (es) {
    lines.push(section('実験サマリー（API）'))
    lines.push(line('生存人口', es.population_alive))
    lines.push(line('人口変化%', es.population_delta_pct))
    lines.push(line('共有資源（合計）', es.resource_pool))
    lines.push(line('交易開放（平均）', es.trade_openness_mean))
    lines.push(line('争い', es.conflicts_total))
    lines.push(line('共同', es.cooperations_total))
    lines.push(line('体制転換', es.regime_shifts))
    lines.push(line('災害', es.disasters))
    lines.push(line('台頭タイプ', es.dominant_archetype))
    if (es.spotlight_agent_id) {
      lines.push(line('スポットライト ID', es.spotlight_agent_id))
      lines.push(line('スポットライト役割', es.spotlight_role))
    }
  }

  const worldSummary = sim.world_summary || sim.last_metrics?.world_summary
  if (worldSummary) {
    lines.push(section('世界の読み取り'))
    lines.push(worldSummary)
    if (sim.last_metrics?.reading_source) {
      lines.push(line('観測ソース', sim.last_metrics.reading_source))
    }
  }

  if (sim.region_readings?.length) {
    lines.push(section('地域観測（最新ターン）'))
    for (const r of sim.region_readings) {
      const label = formatters.regionLabel(r.region_id)
      lines.push(subsection(label))
      lines.push(line('緊張', pct(r.tension)))
      lines.push(line('繁栄', pct(r.prosperity)))
      lines.push(line('不満', pct(r.discontent)))
      lines.push(line('結束', pct(r.cohesion)))
      lines.push(line('台頭タイプ', formatters.archetypeLabel(r.rising_archetype)))
      lines.push(line('軌道', formatters.trajectoryLabel(r.trajectory)))
      lines.push(line('ソース', r.source || '—'))
      if (r.summary) lines.push(r.summary)
    }
  }

  if (sim.region_policies?.length) {
    lines.push(section('地域方針（次ターン）'))
    for (const p of sim.region_policies) {
      lines.push(
        `${formatters.regionLabel(p.region_id)}: ${formatters.actionLabel(p.action)} (強度 ${p.intensity.toFixed(2)}) — ${p.reason}`,
      )
    }
  }

  if (sim.world.regions?.length) {
    lines.push(section('列ごとの環境・社会（スナップショット）'))
    for (const r of sim.world.regions) {
      lines.push(subsection(formatters.regionLabel(r.id)))
      if (r.subregion_id) lines.push(line('サブ地域', r.subregion_id))
      if (r.institution) lines.push(line('制度', formatters.institutionLabel(r.institution)))
      if (r.tax_rate != null) lines.push(line('税率', pct(r.tax_rate)))
      if (r.trade_openness != null) lines.push(line('交易開放', pct(r.trade_openness)))
      if (r.resource_pool != null) lines.push(line('共有資源', r.resource_pool.toFixed(1)))
      if (r.disaster_frequency != null) lines.push(line('災害頻度', pct(r.disaster_frequency)))
    }
  }

  if (sim.settlements?.length) {
    lines.push(section('集落・指導者'))
    const sorted = [...sim.settlements].sort((a, b) => b.member_ids.length - a.member_ids.length)
    for (const s of sorted) {
      const leader = s.leader_id ? sim.agents.find((a) => a.id === s.leader_id) : null
      const region = s.region_id ? formatters.regionLabel(s.region_id) : '—'
      lines.push(
        `${s.id} | ${region} | 人数 ${s.member_ids.length} | 指導者 ${leader ? `${leader.name} (${leader.id})` : '—'}`,
      )
    }
  }

  const leaders = new Set(sim.settlements?.map((s) => s.leader_id).filter(Boolean) as string[])
  if (leaders.size) {
    lines.push(section('指導者の性格（スナップショット）'))
    for (const id of [...leaders].sort()) {
      const agent = sim.agents.find((a) => a.id === id)
      if (!agent) continue
      const p = agent.personality
      lines.push(
        `${agent.name} (${id}) | 野心 ${pct(p?.ambition)} 協調 ${pct(p?.cooperation)} 攻撃 ${pct(p?.aggression)} | traits: ${(agent.traits || []).join(', ') || '—'}`,
      )
    }
  }

  lines.push(section('出来事サマリー（種別ごとの件数）'))
  for (const [action, count] of Object.entries(actionCounts).sort((a, b) => b[1] - a[1])) {
    lines.push(`${formatters.actionLabel(action)}: ${count}`)
  }

  const headlines = events.filter(formatters.isHeadlineEvent)
  if (headlines.length) {
    lines.push(section('主要出来事（災害・体制・集団争いなど）'))
    for (const row of headlines) {
      const year = calendarYearForTurn(sim, row.turn)
      lines.push(
        `[T${row.turn} ${formatters.formatYearLabel(year)}] ${formatters.headlineText(row)}`,
      )
      const detail = formatters.eventDetail(row)
      if (detail) lines.push(`  → ${detail}`)
    }
  }

  lines.push(section('出来事ログ（全件・ターン順）'))
  let currentTurn = -1
  for (const row of events) {
    if (row.turn !== currentTurn) {
      currentTurn = row.turn
      const year = calendarYearForTurn(sim, row.turn)
      lines.push(subsection(`ターン ${row.turn}（${formatters.formatYearLabel(year)}）`))
    }
    const parts = [
      formatters.actionLabel(row.action),
      formatters.actorLabel(row.actor_id),
    ]
    if (row.target_id) parts.push(`→ ${formatters.actorLabel(row.target_id)}`)
    if (row.success === true) parts.push('[成功]')
    if (row.success === false) parts.push('[失敗]')
    if (row.alert) parts.push(`[${row.alert}]`)
    lines.push(`  ${parts.join(' ')}`)
    const detail = formatters.eventDetail(row)
    if (detail) lines.push(`    ${detail}`)
    if (row.detail_key) lines.push(`    detail_key: ${row.detail_key}`)
    if (row.detail && detail !== row.detail) lines.push(`    raw: ${row.detail}`)
    if (row.deltas && Object.keys(row.deltas).length) {
      lines.push(`    deltas: ${JSON.stringify(row.deltas)}`)
    }
    if (row.extra && Object.keys(row.extra).length) {
      lines.push(`    extra: ${JSON.stringify(row.extra)}`)
    }
  }

  lines.push('\n--- end of report ---\n')
  return lines.join('\n')
}

export function milestoneExportFilename(sim: MilestoneExportSim, milestoneYear: number): string {
  const variant = sim.experiment_variant || 'custom'
  const turn = sim.world.turn
  return `civ-${variant}-AD${milestoneYear}-turn${turn}.txt`
}

export function downloadTextFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
