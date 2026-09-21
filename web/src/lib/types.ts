// Shapes the API sends. Kept by hand rather than generated, because there are
// five of them and a generator would be more machinery than the payload.

export type Stage =
  | 'queued'
  | 'resolving'
  | 'fetching'
  | 'hearing'
  | 'judging'
  | 'done'
  | 'failed'

export interface Video {
  id: string
  title: string
  channel: string
  duration: number | null
  thumbnail: string | null
  watchUrl: string
  embedUrl: string
}

/** One percept: what the fly heard, which cells fired, and what it did. */
export interface Frame {
  t: number
  confidence: number
  valence: number
  dopamine: number
  aversion: number
  approach: number
  avoidance: number
  kenyon: number[]
  ear: number[]
}

export interface Summary {
  verdict: boolean
  committedAt: number | null
  firstSuspicionAt: number | null
  peakConfidence: number
  meanConfidence: number
  peakDopamine: number
  peakAversion: number
  fractionAboveHalf: number
  percepts: number
  audioSeconds: number
  videoSeconds: number | null
  analysisSeconds: number
  realtimeFactor: number | null
  commitThreshold: number
}

export interface Circuit {
  receptors: number
  melBands: number
  chromaBands: number
  subframes: number
  kenyonCells: number
  claws: number
  activeKenyonCells: number
  compartments: string[]
  windowSeconds: number
  hopSeconds: number
  commitThreshold: number
  dopamineTau: number
}

export interface TrackScore {
  count: number
  accuracy: number
  recall: number
  specificity: number
  median_latency: number | null
  p90_latency: number | null
}

export interface Evaluation {
  macroAuc: number
  tracks: TrackScore
  percepts: { count: number; accuracy: number; recall: number; specificity: number; auc: number }
  medianFirstSuspicion: number | null
}

export interface BrainCard {
  target: string
  trained: string | null
  calibration: string | null
  corpus: { tracks: number | null; percepts: number | null }
  circuit: Circuit
  performance: {
    unheardUpload: Evaluation | null
    unheardRendition: Evaluation | null
    commitment: string | null
  }
}

/** A track in the training corpus, with what the fly made of it out of fold. */
export interface Spread {
  p05: number
  median: number
  p95: number
  peak: number
  percepts: number
  seconds: number
}

export interface CorpusTrack {
  id: string
  title: string
  kind: string
  group: string
  use: string
  positive: boolean
  watchUrl: string
  spread: Partial<Record<'rendition' | 'upload', Spread>>
  verdict: Partial<Record<'rendition' | 'upload', { committed: boolean; latency: number | null }>>
}

export interface Corpus {
  target: string | null
  curationRules: unknown
  tracks: CorpusTrack[]
  performance: {
    rendition: Record<string, number>
    upload: Record<string, number>
  }
}

/** A span of a video somebody labelled by hand after the fly got it wrong. */
export interface Correction {
  id: string
  at: string
  video_id: string
  label: 'rickroll' | 'not-rickroll'
  start: number
  end: number
  title: string
  url: string
  note: string
  verdict_was: boolean | null
  committed_at: number | null
}
