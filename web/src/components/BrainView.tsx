import { useEffect, useMemo, useRef } from 'react'
import type { Circuit, Frame } from '../lib/types'

interface Props {
  circuit: Circuit
  frame: Frame | null
  live: boolean
}

const WIDTH = 900
const HEIGHT = 560

const INK = {
  bg: '#0d1117',
  edge: '#1d2530',
  outline: '#2b3543',
  quiet: '#39414d',
  ear: '#0094C6',
  chroma: '#52d0f5',
  kenyon: '#c8d3e0',
  dopamine: '#ffb531',
  aversion: '#ff5c7a',
  label: '#5c6672',
}

/** Deterministic scatter, so the calyx looks the same on every render. */
function layoutKenyon(count: number) {
  const points = new Float32Array(count * 2)
  let seed = 1987
  const random = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0
    return seed / 4294967296
  }
  for (let i = 0; i < count; i += 1) {
    // Rejection-sample into an ellipse: the calyx is a blob, not a rectangle.
    let x = 0
    let y = 0
    do {
      x = random() * 2 - 1
      y = random() * 2 - 1
    } while (x * x + y * y > 1)
    points[i * 2] = x
    points[i * 2 + 1] = y
  }
  return points
}

/**
 * The circuit, drawn the way it is wired.
 *
 * Left to right: Johnston's organ as a bank of tonotopic channels and pitch
 * classes, the antennal lobe that normalises them, the calyx where every
 * Kenyon cell is one dot, and the two output compartments with their
 * dopaminergic neurons. Only the cells that are firing are drawn bright, so
 * the sparseness of the code is the thing you actually see.
 *
 * Canvas rather than SVG because 2,000 dots at 8 Hz is 16,000 DOM mutations a
 * second, and the browser has opinions about that.
 */
export default function BrainView({ circuit, frame, live }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const scatter = useMemo(() => layoutKenyon(circuit.kenyonCells), [circuit.kenyonCells])
  const firing = useMemo(() => new Set(frame?.kenyon ?? []), [frame])

  useEffect(() => {
    const element = canvas.current
    if (!element) return
    const ratio = window.devicePixelRatio || 1
    element.width = WIDTH * ratio
    element.height = HEIGHT * ratio
    const ctx = element.getContext('2d')
    if (!ctx) return
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
    ctx.clearRect(0, 0, WIDTH, HEIGHT)

    const dopamine = frame?.dopamine ?? 0
    const aversion = frame?.aversion ?? 0
    const ear = frame?.ear ?? []

    drawEar(ctx, circuit, ear)
    drawAntennalLobe(ctx, ear)
    drawCalyx(ctx, scatter, firing, circuit.kenyonCells, dopamine)
    drawCompartments(ctx, frame, dopamine, aversion)
    drawLabels(ctx, circuit, firing.size, live)
  }, [circuit, frame, firing, scatter, live])

  return (
    <canvas
      ref={canvas}
      className="brain-canvas"
      style={{ width: '100%', aspectRatio: `${WIDTH} / ${HEIGHT}` }}
      role="img"
      aria-label="Live activity in the modelled mushroom body"
    />
  )
}

function drawEar(ctx: CanvasRenderingContext2D, circuit: Circuit, ear: number[]) {
  const x = 46
  const top = 70
  const height = 400
  const bands = circuit.melBands
  const step = height / bands

  ctx.fillStyle = INK.edge
  ctx.fillRect(x - 6, top - 10, 40, height + 20)

  for (let i = 0; i < bands; i += 1) {
    const value = ear[i] ?? 0
    const y = top + (bands - 1 - i) * step
    ctx.fillStyle = INK.quiet
    ctx.fillRect(x, y, 28, step - 1.2)
    if (value > 0.01) {
      ctx.fillStyle = INK.ear
      ctx.globalAlpha = Math.min(1, 0.18 + value)
      ctx.fillRect(x, y, 28 * Math.min(1, value * 1.15), step - 1.2)
      ctx.globalAlpha = 1
    }
  }

  // Pitch classes sit under the tonotopic bank, as their own short row.
  const chromaTop = top + height + 26
  for (let i = 0; i < circuit.chromaBands; i += 1) {
    const value = ear[bands + i] ?? 0
    const y = chromaTop + i * 3.4
    ctx.fillStyle = INK.quiet
    ctx.fillRect(x, y, 28, 2.4)
    if (value > 0.01) {
      ctx.fillStyle = INK.chroma
      ctx.globalAlpha = Math.min(1, 0.2 + value)
      ctx.fillRect(x, y, 28 * Math.min(1, value * 1.15), 2.4)
      ctx.globalAlpha = 1
    }
  }
}

function drawAntennalLobe(ctx: CanvasRenderingContext2D, ear: number[]) {
  // Glomeruli: a column of circles whose brightness pools nearby channels.
  const cx = 150
  const count = 14
  const top = 96
  const gap = 27
  for (let i = 0; i < count; i += 1) {
    const lo = Math.floor((i / count) * ear.length)
    const hi = Math.max(lo + 1, Math.floor(((i + 1) / count) * ear.length))
    let sum = 0
    for (let j = lo; j < hi; j += 1) sum += ear[j] ?? 0
    const value = ear.length ? sum / (hi - lo) : 0

    ctx.beginPath()
    ctx.arc(cx, top + i * gap, 9.5, 0, Math.PI * 2)
    ctx.fillStyle = INK.edge
    ctx.fill()
    ctx.strokeStyle = INK.outline
    ctx.lineWidth = 1
    ctx.stroke()
    if (value > 0.01) {
      ctx.beginPath()
      ctx.arc(cx, top + i * gap, 9.5 * Math.min(1, 0.35 + value), 0, Math.PI * 2)
      ctx.fillStyle = INK.ear
      ctx.globalAlpha = Math.min(1, 0.25 + value)
      ctx.fill()
      ctx.globalAlpha = 1
    }
  }
  ctx.strokeStyle = INK.outline
  ctx.beginPath()
  ctx.moveTo(cx + 14, HEIGHT / 2)
  ctx.lineTo(240, HEIGHT / 2)
  ctx.stroke()
}

function drawCalyx(
  ctx: CanvasRenderingContext2D,
  scatter: Float32Array,
  firing: Set<number>,
  count: number,
  dopamine: number,
) {
  const cx = 430
  const cy = 258
  const rx = 165
  const ry = 180

  ctx.beginPath()
  ctx.ellipse(cx, cy, rx + 16, ry + 14, 0, 0, Math.PI * 2)
  ctx.fillStyle = INK.edge
  ctx.fill()
  ctx.strokeStyle = INK.outline
  ctx.lineWidth = 1.2
  ctx.stroke()

  ctx.fillStyle = INK.quiet
  for (let i = 0; i < count; i += 1) {
    if (firing.has(i)) continue
    ctx.fillRect(cx + scatter[i * 2] * rx, cy + scatter[i * 2 + 1] * ry, 1.7, 1.7)
  }

  const glow = 0.55 + 0.45 * Math.min(1, dopamine)
  ctx.fillStyle = INK.kenyon
  ctx.shadowColor = INK.dopamine
  ctx.shadowBlur = 7 * Math.min(1, dopamine * 1.6)
  for (const i of firing) {
    if (i >= count) continue
    ctx.globalAlpha = glow
    ctx.beginPath()
    ctx.arc(cx + scatter[i * 2] * rx, cy + scatter[i * 2 + 1] * ry, 2.3, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1
  ctx.shadowBlur = 0

  // The peduncle: the bundle of Kenyon axons leaving for the lobes.
  ctx.strokeStyle = INK.outline
  ctx.lineWidth = 1
  for (let i = 0; i < 7; i += 1) {
    ctx.beginPath()
    ctx.moveTo(cx + rx + 8, cy - 30 + i * 10)
    ctx.lineTo(650, i < 4 ? 168 : 372)
    ctx.stroke()
  }
}

function drawCompartments(
  ctx: CanvasRenderingContext2D,
  frame: Frame | null,
  dopamine: number,
  aversion: number,
) {
  const rows = [
    { label: 'MBON approach', y: 168, value: frame?.approach ?? 0, pool: dopamine, ink: INK.dopamine, dan: 'PAM' },
    { label: 'MBON avoidance', y: 372, value: frame?.avoidance ?? 0, pool: aversion, ink: INK.aversion, dan: 'PPL1' },
  ]

  for (const row of rows) {
    ctx.fillStyle = INK.edge
    ctx.strokeStyle = INK.outline
    ctx.lineWidth = 1.2
    roundRect(ctx, 650, row.y - 54, 208, 108, 10)
    ctx.fill()
    ctx.stroke()

    // The dopaminergic neuron for this compartment.
    ctx.beginPath()
    ctx.arc(690, row.y - 22, 13, 0, Math.PI * 2)
    ctx.fillStyle = row.ink
    ctx.globalAlpha = 0.16 + 0.84 * Math.min(1, row.pool)
    ctx.fill()
    ctx.globalAlpha = 1
    ctx.strokeStyle = row.ink
    ctx.globalAlpha = 0.5
    ctx.stroke()
    ctx.globalAlpha = 1

    ctx.font = '600 11px "JetBrains Mono", monospace'
    ctx.fillStyle = row.ink
    ctx.fillText(row.dan, 712, row.y - 18)
    ctx.fillStyle = INK.label
    ctx.font = '400 10px "JetBrains Mono", monospace'
    ctx.fillText(row.label, 668, row.y + 12)

    // Synaptic drive onto the output neuron.
    ctx.fillStyle = INK.quiet
    ctx.fillRect(668, row.y + 22, 172, 7)
    ctx.fillStyle = INK.kenyon
    ctx.fillRect(668, row.y + 22, 172 * Math.max(0, Math.min(1, row.value)), 7)
  }
}

function drawLabels(
  ctx: CanvasRenderingContext2D,
  circuit: Circuit,
  active: number,
  live: boolean,
) {
  ctx.font = '500 10px "JetBrains Mono", monospace'
  ctx.fillStyle = INK.label
  ctx.fillText("Johnston's organ", 20, 54)
  ctx.fillText(`${circuit.melBands} tonotopic + ${circuit.chromaBands} pitch`, 20, 512)
  ctx.fillText('antennal lobe', 112, 76)
  ctx.fillText('mushroom body calyx', 356, 54)
  ctx.fillText(
    `${active}/${circuit.kenyonCells} Kenyon cells firing`,
    356,
    HEIGHT - 44,
  )
  ctx.fillText('lobes', 650, 96)
  if (!live) {
    ctx.fillStyle = INK.outline
    ctx.fillText('at rest', 356, 70)
  }
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
