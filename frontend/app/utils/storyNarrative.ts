import type { RegionObservation, TurnDigestData, NotableEventRef } from '~/utils/turnDigest'

export type StoryRegionMeta = {
  id: string
  subregion_id?: string | null
  institution?: string
  tax_rate?: number
  education_level?: number
  religion?: string
}

type Translate = (key: string, params?: Record<string, unknown>) => string

function polityDescription(
  bands: number,
  cities: number,
  nations: number,
  t: Translate,
): string {
  if (nations > 0) return t('story.polity.nation', { n: nations })
  if (cities > 0) return t('story.polity.city', { n: cities })
  if (bands > 0) return t('story.polity.band', { n: bands })
  return t('story.polity.scatter')
}

export function buildOpeningStory(
  regions: StoryRegionMeta[],
  templateId: string,
  startYear: number,
  t: Translate,
): string {
  const intro = t(`templates.${templateId}.opening`, { year: startYear })
  const lines = regions.map((region) => {
    const tax = Math.round((region.tax_rate ?? 0) * 100)
    return t('story.regionOpening', {
      region: t(`geographies.${region.id}`),
      sub: region.subregion_id ? t(`subregions.${region.subregion_id}`) : '—',
      institution: t(`institutions.${region.institution ?? 'democracy'}`),
      tax,
      religion: t(`religions.${region.religion ?? 'folk'}`),
    })
  })
  return [intro, ...lines].join('\n')
}

export function buildRegionPortrait(
  row: RegionObservation,
  meta: StoryRegionMeta | undefined,
  t: Translate,
): string {
  const tax = Math.round((meta?.tax_rate ?? 0) * 100)
  const polity = polityDescription(row.bands, row.cities, row.nations, t)
  const moodKey =
    row.discontent >= 0.55
      ? 'story.mood.angry'
      : row.tension >= 0.55
        ? 'story.mood.tense'
        : row.prosperity >= 0.55
          ? 'story.mood.prosperous'
          : 'story.mood.calm'
  const archetype = t(`digest.archetypes.${row.risingArchetype}`)
  const trajectory = t(`digest.trajectories.${row.trajectory}`)
  return t('story.regionPortrait', {
    region: t(`geographies.${row.regionId}`),
    polity,
    institution: t(`institutions.${meta?.institution ?? 'democracy'}`),
    tax,
    mood: t(moodKey),
    trajectory,
    archetype: row.risingArchetype === 'none' ? t('story.archetype.none') : archetype,
    population: row.population,
  })
}

function turnHeadline(digest: TurnDigestData, t: Translate): string {
  const { totals } = digest
  if (totals.disasters > 0 || totals.regimeShifts > 0) {
    return t('story.headline.upheaval', { disasters: totals.disasters, regime: totals.regimeShifts })
  }
  if (totals.conflicts > totals.cooperations && totals.conflicts >= 2) {
    return t('story.headline.conflict', { n: totals.conflicts })
  }
  if (totals.cooperations > totals.conflicts && totals.cooperations >= 2) {
    return t('story.headline.cooperation', { n: totals.cooperations })
  }
  if (totals.births + totals.deaths >= 3) {
    return t('story.headline.demography', { births: totals.births, deaths: totals.deaths })
  }
  if (totals.nations > 0 || totals.cities > 0) {
    return t('story.headline.polity', { cities: totals.cities, nations: totals.nations })
  }
  return t('story.headline.quiet', { turn: digest.turn })
}

function regionLabel(id: string, t: Translate): string {
  const geoKey = `geographies.${id}`
  const geo = t(geoKey)
  if (geo !== geoKey) return geo
  const subKey = `subregions.${id}`
  const sub = t(subKey)
  if (sub !== subKey) return sub
  return id
}

function notableToSentence(item: NotableEventRef, t: Translate): string | null {
  const actor = regionLabel(item.actorId, t)
  const key = `story.notable.${item.key}`
  const translated = t(key, {
    group: actor,
    other: item.targetId ? regionLabel(item.targetId, t) : '',
    from: item.extra?.from ? t(`institutions.${item.extra.from}`) : '',
    to: item.extra?.to ? t(`institutions.${item.extra.to}`) : '',
  })
  return translated === key ? null : translated
}

export function buildTurnStory(
  digest: TurnDigestData,
  regions: StoryRegionMeta[],
  t: Translate,
): { headline: string; paragraphs: string[]; regionPortraits: Record<string, string> } {
  const metaById = new Map(regions.map((r) => [r.id, r]))
  const headline = turnHeadline(digest, t)

  const paragraphs: string[] = []
  const notable = digest.notableEvents
    .map((item) => notableToSentence(item, t))
    .filter((line): line is string => Boolean(line))
  if (notable.length) {
    paragraphs.push(notable.join(' '))
  }

  const ranked = [...digest.regionObservations]
    .filter((row) => row.population > 0)
    .sort((a, b) => b.discontent + b.tension - (a.discontent + a.tension))
  const lead = ranked[0]
  if (lead) {
    paragraphs.push(buildRegionPortrait(lead, metaById.get(lead.regionId), t))
  }

  const rising = ranked.find(
    (row) => row.risingArchetype !== 'none' && row.trajectory !== 'stagnation',
  )
  if (rising && rising.regionId !== lead?.regionId) {
    paragraphs.push(
      t('story.secondaryRegion', {
        region: t(`geographies.${rising.regionId}`),
        trajectory: t(`digest.trajectories.${rising.trajectory}`),
        archetype: t(`digest.archetypes.${rising.risingArchetype}`),
      }),
    )
  }

  if (digest.cumulative.regimeShifts > 0 && digest.turn > 1) {
    paragraphs.push(
      t('story.cumulativeRegime', { n: digest.cumulative.regimeShifts }),
    )
  }

  if (!paragraphs.length) {
    paragraphs.push(t('story.quietTurn', { population: digest.totals.population }))
  }

  const regionPortraits: Record<string, string> = {}
  for (const row of digest.regionObservations) {
    if (row.population <= 0) continue
    regionPortraits[row.regionId] = buildRegionPortrait(row, metaById.get(row.regionId), t)
  }

  return { headline, paragraphs, regionPortraits }
}

export function buildOutcomeArc(digest: TurnDigestData, t: Translate): string {
  const { cumulative, totals } = digest
  if (digest.turn < 2) return ''
  return t('story.outcomeArc', {
    turn: digest.turn,
    population: totals.population,
    conflicts: cumulative.conflicts,
    cooperations: cumulative.cooperations,
    disasters: cumulative.disasters,
    regime: cumulative.regimeShifts,
    nations: totals.nations,
    cities: totals.cities,
  })
}
