import { useEffect, useMemo, useRef, useState } from 'react'
import type { Frame } from './types'

/**
 * Turn a playback position in seconds into the frame the fly was in.
 *
 * Percepts are evenly spaced, so the index is arithmetic rather than a search.
 * The frame is the one whose sound had just finished, which is the only one
 * the fly could have been reacting to at that moment.
 */
export function useFrameAt(frames: Frame[], seconds: number): Frame | null {
  return useMemo(() => {
    if (frames.length === 0) return null
    const first = frames[0]?.t ?? 0
    const last = frames[frames.length - 1]?.t ?? first
    const step = frames.length > 1 ? (last - first) / (frames.length - 1) : 1
    const index = Math.round((seconds - first) / (step || 1))
    return frames[Math.max(0, Math.min(frames.length - 1, index))] ?? null
  }, [frames, seconds])
}

/**
 * A clock that replays the fly's response without the video.
 *
 * Used when the embed is blocked, and as the "replay" control. It advances in
 * real time off requestAnimationFrame so it stays in step with the wall clock
 * rather than with the render rate.
 */
export function useReplay(duration: number) {
  const [seconds, setSeconds] = useState(0)
  const [running, setRunning] = useState(false)
  const started = useRef(0)
  const origin = useRef(0)

  useEffect(() => {
    if (!running) return
    started.current = performance.now()
    let raf = 0
    const tick = () => {
      const elapsed = origin.current + (performance.now() - started.current) / 1000
      if (elapsed >= duration) {
        setSeconds(duration)
        setRunning(false)
        return
      }
      setSeconds(elapsed)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [running, duration])

  return {
    seconds,
    running,
    start: (from = 0) => {
      origin.current = from
      setSeconds(from)
      setRunning(true)
    },
    stop: () => setRunning(false),
    seek: (value: number) => {
      origin.current = value
      started.current = performance.now()
      setSeconds(value)
    },
  }
}
