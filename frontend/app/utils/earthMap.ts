export type Ring = [number, number][]

export type Theater = {
  id: string
  west: number
  east: number
  south: number
  north: number
}

export const ISLAND_THEATERS: Theater[] = [
  { id: 'japan', west: 128, east: 146, south: 30, north: 46 },
  { id: 'britain', west: -11, east: 3, south: 49, north: 60 },
  { id: 'maritime_se_asia', west: 95, east: 128, south: -9, north: 19 },
]

export const CONTINENT_THEATERS: Theater[] = [
  { id: 'east_asia', west: 95, east: 145, south: 18, north: 53 },
  { id: 'europe', west: -10, east: 40, south: 35, north: 60 },
  { id: 'africa', west: -18, east: 42, south: -30, north: 32 },
  { id: 'north_america', west: -125, east: -70, south: 25, north: 50 },
]

const LAND: Ring[] = [
  // Africa
  [[-17, 21], [-16, 16], [-17, 12], [-16, 5], [-8, 4], [0, 5], [8, 4], [10, 1], [9, -2], [12, -6], [13, -10], [12, -16], [14, -22], [18, -34], [20, -35], [25, -34], [30, -30], [32, -29], [29, -26], [33, -26], [36, -24], [35, -20], [40, -15], [42, -12], [40, -3], [43, 0], [48, 5], [51, 12], [43, 12], [40, 16], [38, 21], [35, 28], [32, 31], [30, 31], [25, 32], [20, 32], [10, 33], [5, 32], [-2, 35], [-6, 36], [-10, 32], [-15, 28]],
  // Europe + western Russia
  [[-9, 43], [-9, 38], [-6, 36], [-5, 36], [0, 39], [3, 39], [10, 38], [16, 38], [20, 40], [26, 40], [29, 41], [30, 46], [28, 45], [29, 47], [36, 45], [40, 47], [38, 50], [30, 52], [30, 56], [28, 59], [24, 60], [20, 60], [12, 58], [8, 57], [5, 58], [8, 63], [12, 66], [16, 69], [25, 71], [40, 68], [44, 66], [50, 68], [60, 70], [66, 72], [60, 64], [50, 60], [48, 54], [46, 48], [40, 44], [38, 40], [32, 36], [28, 36], [22, 37], [16, 40], [12, 42], [8, 44], [3, 43], [-1, 44], [-5, 48], [-5, 52], [-6, 56], [-5, 58], [-2, 58], [0, 53], [-2, 50], [-5, 50], [-5, 48], [-9, 43]],
  // Scandinavia
  [[5, 58], [8, 63], [12, 66], [16, 69], [20, 70], [25, 71], [20, 63], [18, 59], [12, 58], [8, 57]],
  // British Isles
  [[-5, 50], [-2, 50], [1, 51], [0, 53], [-2, 56], [-5, 58], [-6, 56], [-5, 54], [-5, 52]],
  [[-10, 52], [-6, 52], [-6, 55], [-8, 55], [-10, 54]],
  // Asia (main)
  [[44, 36], [48, 30], [54, 27], [57, 26], [60, 25], [66, 25], [70, 22], [73, 18], [77, 8], [80, 6], [80, 10], [85, 20], [88, 22], [92, 21], [94, 18], [98, 10], [102, 2], [104, 1], [109, 2], [109, 14], [108, 22], [110, 20], [114, 22], [118, 24], [122, 30], [122, 38], [124, 40], [128, 38], [130, 42], [132, 43], [128, 48], [132, 46], [138, 46], [142, 47], [140, 50], [136, 54], [140, 58], [150, 59], [160, 62], [170, 66], [180, 68], [180, 72], [160, 72], [140, 72], [120, 74], [100, 76], [80, 72], [70, 70], [60, 70], [50, 68], [44, 66], [40, 60], [42, 54], [46, 48], [44, 42], [42, 38]],
  // India
  [[68, 24], [72, 21], [73, 16], [77, 8], [80, 6], [82, 8], [80, 15], [85, 22], [80, 24], [74, 24]],
  // SE Asia / Indochina
  [[98, 10], [102, 2], [104, 1], [105, 6], [103, 12], [100, 14], [98, 12]],
  // Sumatra / Java / Borneo / Philippines / New Guinea (island chains)
  [[95, 5], [98, 3], [104, -3], [106, -6], [110, -8], [114, -8], [115, -4], [110, 0], [104, 1], [98, 2]],
  [[109, 3], [113, 1], [118, 3], [119, 7], [116, 7], [110, 5]],
  [[120, 6], [122, 8], [126, 12], [125, 18], [122, 18], [120, 14], [119, 8]],
  [[131, -1], [138, -5], [146, -8], [151, -10], [147, -4], [140, -2], [134, 0]],
  // Japan
  [[140, 42], [145, 43], [145, 45], [142, 45], [140, 43]],
  [[131, 34], [136, 34], [138, 35], [141, 36], [141, 39], [140, 41], [139, 37], [136, 36], [135, 35], [133, 34]],
  [[130, 31], [132, 32], [131, 34], [130, 33]],
  [[133, 33], [134.5, 34], [133.5, 34.2]],
  // Korea
  [[126, 34], [129, 35], [130, 38], [128, 39], [125, 38], [126, 35]],
  // Taiwan
  [[120, 22], [122, 22], [122, 25], [120, 25]],
  // Australia
  [[114, -22], [114, -28], [116, -34], [122, -34], [130, -32], [136, -35], [142, -38], [150, -38], [153, -28], [151, -22], [146, -16], [142, -12], [136, -12], [128, -14], [122, -16], [118, -20]],
  // Tasmania / NZ
  [[145, -41], [148, -41], [148, -43], [145, -43]],
  [[166, -46], [170, -46], [176, -41], [178, -37], [175, -36], [172, -41], [168, -44]],
  // Greenland
  [[-73, 78], [-60, 82], [-40, 83], [-20, 80], [-22, 72], [-30, 68], [-44, 60], [-50, 64], [-60, 70], [-70, 76]],
  // North America
  [[-168, 66], [-164, 64], [-160, 66], [-150, 68], [-140, 70], [-128, 70], [-120, 69], [-110, 68], [-100, 68], [-90, 70], [-84, 66], [-80, 62], [-70, 60], [-64, 58], [-62, 54], [-60, 50], [-64, 48], [-66, 44], [-70, 42], [-74, 40], [-76, 36], [-80, 32], [-82, 28], [-82, 25], [-80, 25], [-81, 28], [-84, 30], [-90, 29], [-94, 29], [-97, 26], [-97, 22], [-100, 20], [-105, 22], [-110, 24], [-114, 27], [-115, 32], [-117, 33], [-122, 36], [-124, 40], [-124, 46], [-128, 50], [-132, 54], [-136, 58], [-148, 60], [-160, 58], [-166, 60], [-168, 66]],
  // Alaska / far east wrap
  [[-168, 66], [-170, 64], [-180, 66], [-180, 70], [-170, 68]],
  [[180, 66], [170, 64], [170, 68], [180, 70]],
  // Central America
  [[-97, 22], [-92, 18], [-88, 16], [-84, 10], [-80, 8], [-78, 9], [-82, 14], [-88, 15], [-92, 18]],
  // Cuba / Hispaniola
  [[-85, 22], [-77, 21], [-74, 20], [-78, 23], [-84, 23]],
  // South America
  [[-81, 1], [-78, 8], [-72, 12], [-68, 11], [-62, 10], [-60, 8], [-52, 5], [-50, 0], [-48, -2], [-44, -3], [-38, -8], [-35, -8], [-35, -12], [-39, -16], [-40, -22], [-44, -24], [-48, -28], [-50, -30], [-52, -32], [-58, -38], [-62, -40], [-65, -43], [-68, -50], [-68, -54], [-71, -52], [-74, -48], [-73, -42], [-72, -36], [-71, -30], [-72, -20], [-76, -14], [-78, -8], [-80, -4], [-81, 1]],
  // Madagascar
  [[43, -12], [50, -13], [47, -25], [44, -25], [43, -16]],
  // Iceland
  [[-24, 64], [-14, 64], [-13, 66], [-20, 66]],
  // Sri Lanka
  [[80, 6], [82, 6], [82, 8], [80, 8]],
]

function lonLatToXy(lon: number, lat: number, w: number, h: number): [number, number] {
  return [((lon + 180) / 360) * w, ((90 - lat) / 180) * h]
}

function landColor(lat: number): [number, number, number] {
  const a = Math.abs(lat)
  if (a > 72) return [228, 236, 242]
  if (a > 62) return [170, 186, 168]
  if (a < 12) return [46, 112, 72]
  if (a < 28) return [168, 148, 86]
  return [72, 122, 78]
}

function drawRing(ctx: CanvasRenderingContext2D, ring: Ring, w: number, h: number, lonShift: number) {
  ctx.beginPath()
  ring.forEach(([lon, lat], i) => {
    const [x, y] = lonLatToXy(lon + lonShift, lat, w, h)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.closePath()
  ctx.fill()
}

export function pickTheater(geography: string | undefined, seed: number): Theater {
  const list = geography === 'continent' ? CONTINENT_THEATERS : ISLAND_THEATERS
  return list[Math.abs(seed) % list.length]
}

export function simToLatLon(x: number, y: number, theater: Theater): { lat: number; lon: number } {
  return {
    lon: theater.west + (x / 100) * (theater.east - theater.west),
    lat: theater.north - (y / 100) * (theater.north - theater.south),
  }
}

export function theaterCenter(theater: Theater): { lat: number; lon: number } {
  return {
    lon: (theater.west + theater.east) / 2,
    lat: (theater.south + theater.north) / 2,
  }
}

export function theaterSpan(theater: Theater): number {
  return Math.max(theater.east - theater.west, theater.north - theater.south)
}

export function createEarthCanvases(width = 2048) {
  const height = width / 2
  const color = document.createElement('canvas')
  color.width = width
  color.height = height
  const rough = document.createElement('canvas')
  rough.width = width
  rough.height = height
  const cctx = color.getContext('2d')
  const rctx = rough.getContext('2d')
  if (!cctx || !rctx) return { color, rough }

  const ocean = cctx.createLinearGradient(0, 0, 0, height)
  ocean.addColorStop(0, '#15324a')
  ocean.addColorStop(0.5, '#0b2438')
  ocean.addColorStop(1, '#15324a')
  cctx.fillStyle = ocean
  cctx.fillRect(0, 0, width, height)

  for (let i = 0; i < 8; i++) {
    const y = ((i + 1) / 9) * height
    cctx.strokeStyle = 'rgba(120, 160, 190, 0.06)'
    cctx.lineWidth = 1
    cctx.beginPath()
    cctx.moveTo(0, y)
    cctx.lineTo(width, y)
    cctx.stroke()
  }
  for (let i = 0; i < 12; i++) {
    const x = (i / 12) * width
    cctx.strokeStyle = 'rgba(120, 160, 190, 0.05)'
    cctx.beginPath()
    cctx.moveTo(x, 0)
    cctx.lineTo(x, height)
    cctx.stroke()
  }

  rctx.fillStyle = '#4a4a4a'
  rctx.fillRect(0, 0, width, height)

  for (const ring of LAND) {
    const midLat = ring.reduce((s, p) => s + p[1], 0) / ring.length
    const [cr, cg, cb] = landColor(midLat)
    cctx.fillStyle = `rgb(${cr}, ${cg}, ${cb})`
    drawRing(cctx, ring, width, height, 0)
    drawRing(cctx, ring, width, height, 360)
    drawRing(cctx, ring, width, height, -360)
    rctx.fillStyle = '#c8c8c8'
    drawRing(rctx, ring, width, height, 0)
    drawRing(rctx, ring, width, height, 360)
    drawRing(rctx, ring, width, height, -360)
  }

  cctx.strokeStyle = 'rgba(180, 220, 200, 0.22)'
  cctx.lineWidth = 1.2
  for (const ring of LAND) {
    cctx.beginPath()
    ring.forEach(([lon, lat], i) => {
      const [x, y] = lonLatToXy(lon, lat, width, height)
      if (i === 0) cctx.moveTo(x, y)
      else cctx.lineTo(x, y)
    })
    cctx.closePath()
    cctx.stroke()
  }

  const ice = cctx.createLinearGradient(0, 0, 0, height * 0.12)
  ice.addColorStop(0, 'rgba(236, 244, 250, 0.95)')
  ice.addColorStop(1, 'rgba(236, 244, 250, 0)')
  cctx.fillStyle = ice
  cctx.fillRect(0, 0, width, height * 0.1)
  const iceS = cctx.createLinearGradient(0, height * 0.88, 0, height)
  iceS.addColorStop(0, 'rgba(236, 244, 250, 0)')
  iceS.addColorStop(1, 'rgba(236, 244, 250, 0.95)')
  cctx.fillStyle = iceS
  cctx.fillRect(0, height * 0.9, width, height * 0.1)

  return { color, rough }
}

export function paintTheater(color: HTMLCanvasElement, theater: Theater | null) {
  const ctx = color.getContext('2d')
  if (!ctx || !theater) return
  const w = color.width
  const h = color.height
  const [x1, y1] = lonLatToXy(theater.west, theater.north, w, h)
  const [x2, y2] = lonLatToXy(theater.east, theater.south, w, h)
  ctx.save()
  ctx.strokeStyle = 'rgba(255, 214, 120, 0.85)'
  ctx.lineWidth = 3
  ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
  ctx.fillStyle = 'rgba(255, 214, 120, 0.08)'
  ctx.fillRect(x1, y1, x2 - x1, y2 - y1)
  ctx.restore()
}
