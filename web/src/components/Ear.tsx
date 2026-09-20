import { useEffect, useRef } from 'react'
import type { Circuit, Frame } from '../lib/types'

interface Props {
  circuit: Circuit
  frame: Frame | null
}

const W = 600
const H = 84

/**
 * The receptors, drawn flat.
 *
 * Johnston's organ sits in the antenna, outside the brain and outside the
 * connectome the 3D view is built from, so it is not in that scene. It is here
 * instead: 48 tonotopic channels along the strip and the 12 pitch classes
 * beneath them, which together are the 180 numbers -- three sub-frames of
 * sixty -- that every percept starts as.
 */
export default function Ear({ circuit, frame }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const element = canvas.current
    if (!element) return
    const ratio = Math.min(window.devicePixelRatio || 1, 2)
    element.width = W * ratio
    element.height = H * ratio
    const ctx = element.getContext('2d')
    if (!ctx) return
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
    ctx.clearRect(0, 0, W, H)

    const ear = frame?.ear ?? []
    const mel = circuit.melBands
    const melTop = 4
    const melHeight = 52
    const step = W / mel

    for (let i = 0; i < mel; i += 1) {
      const value = Math.max(0, Math.min(1, ear[i] ?? 0))
      const x = i * step
      ctx.fillStyle = '#17140f'
      ctx.fillRect(x, melTop, step - 1, melHeight)
      if (value > 0.004) {
        const h = melHeight * value
        ctx.fillStyle = '#c9a227'
        ctx.globalAlpha = 0.35 + 0.65 * value
        ctx.fillRect(x, melTop + melHeight - h, step - 1, h)
        ctx.globalAlpha = 1
      }
    }

    const chromaTop = melTop + melHeight + 8
    const chromaStep = W / circuit.chromaBands
    for (let i = 0; i < circuit.chromaBands; i += 1) {
      const value = Math.max(0, Math.min(1, ear[mel + i] ?? 0))
      const x = i * chromaStep
      ctx.fillStyle = '#17140f'
      ctx.fillRect(x, chromaTop, chromaStep - 2, 14)
      if (value > 0.004) {
        ctx.fillStyle = '#8a6fb0'
        ctx.globalAlpha = 0.35 + 0.65 * value
        ctx.fillRect(x, chromaTop, (chromaStep - 2) * value, 14)
        ctx.globalAlpha = 1
      }
    }
  }, [circuit, frame])

  return (
    <canvas
      ref={canvas}
      className="ear-canvas"
      style={{ aspectRatio: `${W} / ${H}` }}
      role="img"
      aria-label="Tonotopic channels and pitch classes for the current percept"
    />
  )
}
