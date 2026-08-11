const SETTLEMENT_HUES = [0, 207, 122, 48, 291, 174, 16, 231, 187, 88]

export function settlementHue(id: string | null): number {
  if (!id) return 210
  const match = id.match(/(\d+)$/)
  const idx = match ? Number(match[1]) - 1 : 0
  return SETTLEMENT_HUES[((idx % SETTLEMENT_HUES.length) + SETTLEMENT_HUES.length) % SETTLEMENT_HUES.length]
}

export function settlementColor(id: string | null, role: 'base' | 'member' | 'leader' = 'base'): string {
  const hue = settlementHue(id)
  if (!id) return 'hsl(210 12% 52%)'
  if (role === 'leader') return `hsl(${hue} 78% 38%)`
  if (role === 'member') return `hsl(${hue} 52% 68%)`
  return `hsl(${hue} 65% 56%)`
}

export function agentFill(agent: { id: string; settlement_id: string | null; traits?: string[] }, isLeader: boolean): string {
  if (agent.settlement_id) return settlementColor(agent.settlement_id, isLeader ? 'leader' : 'member')
  let hash = 0
  for (let i = 0; i < agent.id.length; i++) hash = (hash * 31 + agent.id.charCodeAt(i)) >>> 0
  const sat = (agent.traits?.length ?? 0) > 0 ? 48 : 28
  const light = (agent.traits?.length ?? 0) > 0 ? 46 : 58
  return `hsl(${hash % 360} ${sat}% ${light}%)`
}

export function agentMark(agent: { traits?: string[] }): string {
  const traits = agent.traits ?? []
  let mark = ''
  if (traits.includes('charisma')) mark += '★'
  if (traits.includes('genius')) mark += '◆'
  return mark
}
