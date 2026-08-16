const PALETTE = [
  '#3d8bfd',
  '#e85d4c',
  '#2bb673',
  '#f0b429',
  '#9b59d0',
  '#1abc9c',
  '#e67e22',
  '#5b6cff',
  '#c0392b',
  '#27ae60',
  '#d35400',
  '#3498db',
] as const

const LONE = '#8b98a8'

export function settlementIndex(id: string | null): number {
  if (!id) return -1
  const match = id.match(/(\d+)$/)
  if (match) {
    return (((Number(match[1]) - 1) % PALETTE.length) + PALETTE.length) % PALETTE.length
  }
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  return hash % PALETTE.length
}

export function hexRgba(hex: string, alpha: number): string {
  const n = Number.parseInt(hex.replace('#', ''), 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function mixHex(hex: string, toward: number, t: number): string {
  const n = Number.parseInt(hex.replace('#', ''), 16)
  const mix = (c: number) => Math.round(c + (toward - c) * t)
  const r = mix((n >> 16) & 255)
  const g = mix((n >> 8) & 255)
  const b = mix(n & 255)
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`
}

export function settlementColor(id: string | null, role: 'base' | 'member' | 'leader' = 'base'): string {
  if (!id) return LONE
  const hex = PALETTE[settlementIndex(id)] ?? PALETTE[0]
  if (role === 'leader') return mixHex(hex, 0, 0.28)
  if (role === 'member') return mixHex(hex, 255, 0.22)
  return hex
}

export function agentFill(agent: { id: string; settlement_id: string | null; traits?: string[] }, isLeader: boolean): string {
  if (agent.settlement_id) return settlementColor(agent.settlement_id, isLeader ? 'leader' : 'member')
  let hash = 0
  for (let i = 0; i < agent.id.length; i++) hash = (hash * 31 + agent.id.charCodeAt(i)) >>> 0
  return PALETTE[hash % PALETTE.length] ?? LONE
}

export function agentMark(agent: { traits?: string[] }): string {
  const traits = agent.traits ?? []
  let mark = ''
  if (traits.includes('charisma')) mark += '★'
  if (traits.includes('genius')) mark += '◆'
  return mark
}

export function polityKind(memberCount: number): 'band' | 'city' | 'nation' {
  if (memberCount >= 20) return 'nation'
  if (memberCount >= 8) return 'city'
  return 'band'
}
