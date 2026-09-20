import type { BrainCard, Frame, Stage, Summary, Video } from './types'

export class ApiError extends Error {}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(body?.detail ?? `${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export async function fetchBrain(): Promise<BrainCard> {
  return readJson<BrainCard>(await fetch('/api/brain'))
}

export async function submit(url: string): Promise<{ id: string; events: string }> {
  return readJson(
    await fetch('/api/analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    }),
  )
}

export interface StreamHandlers {
  onStage(stage: Stage): void
  onVideo(video: Video): void
  onMedia(url: string): void
  onHeard(percepts: number, seconds: number): void
  onTimeline(from: number, frames: Frame[]): void
  onSummary(summary: Summary): void
  onError(message: string): void
}

/**
 * Follow one analysis. Returns a function that closes the stream.
 *
 * The server sends the timeline in chunks, each one a struct of arrays; this
 * transposes them into frames so the rest of the app works with one object per
 * percept rather than nine parallel arrays.
 */
export function stream(jobId: string, handlers: StreamHandlers): () => void {
  const source = new EventSource(`/api/analysis/${jobId}/events`)

  source.addEventListener('stage', (event) => {
    const data = JSON.parse((event as MessageEvent).data)
    handlers.onStage(data.stage)
    if (data.stage === 'done' || data.stage === 'failed') source.close()
  })
  source.addEventListener('video', (event) => {
    handlers.onVideo(JSON.parse((event as MessageEvent).data).video)
  })
  source.addEventListener('media', (event) => {
    handlers.onMedia(JSON.parse((event as MessageEvent).data).url)
  })
  source.addEventListener('heard', (event) => {
    const data = JSON.parse((event as MessageEvent).data)
    handlers.onHeard(data.percepts, data.seconds)
  })
  source.addEventListener('timeline', (event) => {
    const d = JSON.parse((event as MessageEvent).data)
    const frames: Frame[] = d.t.map((t: number, i: number) => ({
      t,
      confidence: d.confidence[i],
      valence: d.valence[i],
      dopamine: d.dopamine[i],
      aversion: d.aversion[i],
      approach: d.approach[i],
      avoidance: d.avoidance[i],
      kenyon: d.kenyon[i],
      ear: d.ear[i],
    }))
    handlers.onTimeline(d.from, frames)
  })
  source.addEventListener('summary', (event) => {
    handlers.onSummary(JSON.parse((event as MessageEvent).data).summary)
  })
  source.addEventListener('error', (event) => {
    const message = (event as MessageEvent).data
    if (message) handlers.onError(JSON.parse(message).message)
    else if (source.readyState === EventSource.CLOSED) handlers.onError('The stream closed.')
  })

  return () => source.close()
}
