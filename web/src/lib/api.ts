import type {
  BrainCard,
  Health,
  JobState,
  ModelState,
  Run,
  Corpus,
  Correction,
  Frame,
  Stage,
  Summary,
  Video,
} from './types'

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

export async function fetchHealth(): Promise<Health> {
  return readJson<Health>(await fetch('/api/health'))
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

export async function fetchCorpus(): Promise<Corpus> {
  return readJson<Corpus>(await fetch('/api/corpus'))
}

export async function fetchCorrections(): Promise<{ count: number; corrections: Correction[] }> {
  return readJson(await fetch('/api/corrections'))
}

export async function postCorrection(body: {
  videoId: string
  label: 'rickroll' | 'not-rickroll'
  start: number
  end: number
  title?: string
  url?: string
  note?: string
  verdictWas?: boolean | null
  committedAt?: number | null
}): Promise<Correction> {
  return readJson<Correction>(
    await fetch('/api/corrections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  )
}

export async function fetchNotes(): Promise<string> {
  return (await readJson<{ text: string }>(await fetch('/api/notes'))).text
}

export async function saveNotes(text: string): Promise<void> {
  await readJson(
    await fetch('/api/notes', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  )
}

export async function fetchModels(): Promise<ModelState> {
  return readJson<ModelState>(await fetch('/api/models'))
}

export async function chooseModel(sense: string, name: string | null): Promise<ModelState> {
  return readJson<ModelState>(
    await fetch('/api/models/active', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sense, name }),
    }),
  )
}

export async function fetchJobs(): Promise<JobState> {
  return readJson<JobState>(await fetch('/api/jobs'))
}

export async function startJob(job: string, options: Record<string, unknown>): Promise<Run> {
  return readJson<Run>(
    await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job, options }),
    }),
  )
}

export async function fetchRun(id: string, tail = 400): Promise<Run> {
  return readJson<Run>(await fetch(`/api/jobs/${id}?tail=${tail}`))
}

export async function stopRun(id: string): Promise<Run> {
  return readJson<Run>(await fetch(`/api/jobs/${id}/stop`, { method: 'POST' }))
}

export interface StreamHandlers {
  onStage(stage: Stage): void
  onVideo(video: Video): void
  onMedia(url: string | null): void
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
    handlers.onStage(JSON.parse((event as MessageEvent).data).stage)
  })
  // The server says when it has nothing left to send. `done` is not that
  // moment: the video is still downloading behind the verdict, and closing
  // there threw away the event carrying its address.
  source.addEventListener('end', () => source.close())
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
