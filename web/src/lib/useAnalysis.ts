import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, stream, submit } from './api'
import type { Frame, Stage, Summary, Video } from './types'

export interface AnalysisState {
  stage: Stage | 'idle'
  video: Video | null
  mediaUrl: string | null
  frames: Frame[]
  expected: number | null
  summary: Summary | null
  error: string | null
}

const EMPTY: AnalysisState = {
  stage: 'idle',
  video: null,
  mediaUrl: null,
  frames: [],
  expected: null,
  summary: null,
  error: null,
}

/**
 * Owns one analysis at a time.
 *
 * Chunks can in principle arrive out of order, so frames are written at their
 * own index rather than appended, and the array is grown to fit.
 */
export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>(EMPTY)
  const close = useRef<null | (() => void)>(null)

  useEffect(() => () => close.current?.(), [])

  const run = useCallback(async (url: string) => {
    close.current?.()
    setState({ ...EMPTY, stage: 'queued' })
    try {
      const { id } = await submit(url)
      close.current = stream(id, {
        onStage: (stage) => setState((s) => ({ ...s, stage })),
        onVideo: (video) => setState((s) => ({ ...s, video })),
        onMedia: (mediaUrl) => setState((s) => ({ ...s, mediaUrl })),
        onHeard: (percepts) => setState((s) => ({ ...s, expected: percepts })),
        onTimeline: (from, chunk) =>
          setState((s) => {
            const frames = s.frames.slice()
            if (frames.length < from + chunk.length) frames.length = from + chunk.length
            chunk.forEach((frame, i) => {
              frames[from + i] = frame
            })
            return { ...s, frames }
          }),
        onSummary: (summary) => setState((s) => ({ ...s, summary })),
        onError: (error) => setState((s) => ({ ...s, error, stage: 'failed' })),
      })
    } catch (error) {
      setState((s) => ({
        ...s,
        stage: 'failed',
        error: error instanceof ApiError ? error.message : String(error),
      }))
    }
  }, [])

  const reset = useCallback(() => {
    close.current?.()
    setState(EMPTY)
  }, [])

  return { ...state, run, reset }
}
