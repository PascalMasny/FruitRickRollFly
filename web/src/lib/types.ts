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
