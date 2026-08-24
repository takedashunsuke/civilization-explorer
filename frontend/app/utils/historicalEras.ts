/** Astronomical year: AD 0 = 0, AD 1 = 1, BC 1 = 0. */

import { JAPAN_NENGO, type JapanNengo } from './japanNengo'

export type CalendarEra = 'bc' | 'ad'

export type PeriodDef = {
  /** Inclusive start (astronomical year) */
  from: number
  /** Exclusive end (astronomical year). Use Infinity for open-ended. */
  to: number
  key: string
}

/** Broad Japan periods (pre-nengō orientation + schoolbook eras). */
export const JAPAN_PERIODS: PeriodDef[] = [
  { from: -Number.POSITIVE_INFINITY, to: -14000, key: 'paleolithic' },
  { from: -14000, to: -300, key: 'jomon' },
  { from: -300, to: 300, key: 'yayoi' },
  { from: 300, to: 538, key: 'kofun' },
  { from: 538, to: 710, key: 'asuka' },
  { from: 710, to: 794, key: 'nara' },
  { from: 794, to: 1185, key: 'heian' },
  { from: 1185, to: 1333, key: 'kamakura' },
  { from: 1333, to: 1573, key: 'muromachi' },
  { from: 1573, to: 1603, key: 'azuchiMomoyama' },
  { from: 1603, to: 1868, key: 'edo' },
  { from: 1868, to: 1912, key: 'meiji' },
  { from: 1912, to: 1926, key: 'taisho' },
  { from: 1926, to: 1989, key: 'showa' },
  { from: 1989, to: 2019, key: 'heisei' },
  { from: 2019, to: Number.POSITIVE_INFINITY, key: 'reiwa' },
]

/** Broad world / global periods for orientation. */
export const WORLD_PERIODS: PeriodDef[] = [
  { from: -Number.POSITIVE_INFINITY, to: -10000, key: 'paleolithic' },
  { from: -10000, to: -3000, key: 'neolithic' },
  { from: -3000, to: -1200, key: 'bronzeAge' },
  { from: -1200, to: -500, key: 'ironAge' },
  { from: -500, to: 500, key: 'classical' },
  { from: 500, to: 1000, key: 'earlyMiddleAges' },
  { from: 1000, to: 1500, key: 'middleAges' },
  { from: 1500, to: 1800, key: 'earlyModern' },
  { from: 1800, to: 1945, key: 'modern' },
  { from: 1945, to: Number.POSITIVE_INFINITY, key: 'contemporary' },
]

const MODERN_PERIOD_KEYS = new Set(['meiji', 'taisho', 'showa', 'heisei', 'reiwa'])

export function toAstronomicalYear(era: CalendarEra, year: number): number {
  if (era === 'ad') return Math.max(0, Math.floor(year))
  const n = Math.max(1, Math.floor(Math.abs(year)))
  return 1 - n
}

export function fromAstronomicalYear(astro: number): { era: CalendarEra; year: number } {
  const y = Math.trunc(astro)
  if (y >= 0) return { era: 'ad', year: y }
  return { era: 'bc', year: 1 - y }
}

export function findPeriod(periods: PeriodDef[], astroYear: number): PeriodDef {
  const y = Math.trunc(astroYear)
  for (const p of periods) {
    if (y >= p.from && y < p.to) return p
  }
  return periods[periods.length - 1]!
}

export function japanPeriodKey(astroYear: number): string {
  return findPeriod(JAPAN_PERIODS, astroYear).key
}

export function worldPeriodKey(astroYear: number): string {
  return findPeriod(WORLD_PERIODS, astroYear).key
}

export function findJapanNengo(astroYear: number): JapanNengo | null {
  const y = Math.trunc(astroYear)
  if (y < 645) return null
  for (const n of JAPAN_NENGO) {
    if (y >= n.from && y < n.to) return n
  }
  return null
}

/**
 * Japan label: schoolbook period + nengō when available.
 * Example: 奈良時代・和銅 / Nara · Wadō
 */
export function formatJapanEraLabel(
  astroYear: number,
  periodLabel: string,
  locale: string,
): string {
  const nengo = findJapanNengo(astroYear)
  const periodKey = japanPeriodKey(astroYear)
  if (!nengo) return periodLabel

  const nengoLabel =
    locale === 'ja' ? `${nengo.ja}（${nengo.reading}）` : `${nengo.en} (${nengo.ja})`

  if (MODERN_PERIOD_KEYS.has(periodKey)) return nengoLabel
  return `${periodLabel}・${nengoLabel}`
}
