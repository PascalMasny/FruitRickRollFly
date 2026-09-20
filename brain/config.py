"""Every tunable number of the fly, in one place.

The values are grouped the way the circuit is: what the ear delivers, what the
first relay does to it, how the mushroom body encodes it, and how dopamine
turns that encoding into behaviour. Where a number comes from the Drosophila
literature the docstring says so; where it is an engineering choice it says
that too. See docs/BRAIN.md for the full mapping.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

# ── Johnston's organ: the ear ────────────────────────────────────────────────

SAMPLE_RATE = 22_050
"""Working sample rate. 11 kHz of usable bandwidth, which is more than the
fly has and enough for every cue that identifies a pop song."""

N_FFT = 1024
"""46.4 ms analysis window."""

FRAME_HOP = 256
"""11.6 ms between spectral frames, so 86.13 frames per second."""

N_MEL = 48
"""Mel bands, read as tonotopic channels of Johnston's organ. The real organ
has roughly 480 neurons in five functional groups; 48 bands is the resolution
this model works at."""

N_CHROMA = 12
"""Pitch classes. Not a fly structure at all; an engineering channel that makes
harmony legible, and the cue that survives a piano cover when timbre does
not."""

CHROMA_N_FFT = 4096
"""Chroma gets its own, longer transform: 186 ms and 5.4 Hz bins. At the 1024
point window the mel bands use, a bin is 21.5 Hz wide, which is three
semitones at the bottom of the bass range; the pitch classes down there came
out as noise. Measured effect of the change on held-out renditions: AUC 0.802
to 0.828."""

CHROMA_TOLERANCE_CENTS = 35.0
"""A bin only votes for a pitch class if it sits within this much of the
semitone centre. Bins between two semitones are discarded rather than
smeared across both."""

MEL_FMIN = 40.0
MEL_FMAX = 8_000.0
CHROMA_FMIN = 55.0
CHROMA_FMAX = 2_100.0

SUBFRAME_FRAMES = 22
"""255 ms per sub-frame: about half a beat at the 113 BPM of the target song."""

SUBFRAMES = 3
"""Three sub-frames per percept, so the fly decides on 801 ms of sound. Roughly
one and a half beats of the target song."""

WINDOW_HOP_FRAMES = 11
"""128 ms between percepts, so the circuit updates 7.8 times a second."""

TARGET_RMS = 0.1
"""Tracks are levelled to this RMS before anything else. The gain control below
needs an absolute reference to tell silence from a quiet passage."""

# ── Antennal-lobe-style gain control ─────────────────────────────────────────

AL_EXPONENT = 1.5
AL_SIGMA = 0.05
AL_SUPPRESSION = 0.05
AL_RMAX = 1.0
"""Divisive normalisation after Olsen, Bhandawat & Wilson (2010). The exponent
and the shape of the denominator are theirs; sigma and the suppression
coefficient are fitted to the dynamic range of music rather than of odour."""

# ── Mushroom body ────────────────────────────────────────────────────────────

N_KENYON = 4_000
"""Kenyon cells. The connectome counts about 2,000 per hemisphere in the adult
Drosophila, and a fly has two, so this is one whole animal's worth. Using both
is worth 0.03 AUC over using one, which is the best return of any parameter in
this file and the only one where the justification is simply that the fly
really does have that many."""

N_CLAWS = 20
"""Dendritic claws per Kenyon cell. Each claw samples one projection neuron at
random, which is the fly's locality-sensitive hash (Dasgupta, Stevens &
Navlakha 2017).

The fly grows about six claws and has about fifty projection neurons to
choose from. What carries the computation is the *ratio*, and this model's
input layer is larger than a fly's, so the ratio is what is preserved:
20 of 180 is 11 percent, against the fly's 12. Holding the absolute count at
six instead costs 0.03 AUC on held-out renditions, because six claws out of
180 see too little of the percept to say anything."""

KC_SPARSITY = 0.05
"""Fraction of Kenyon cells the APL neuron leaves unsilenced, matching the
measured sparseness of the real code. 5 percent of 4,000 is 200 cells firing
per percept.

At 2,000 cells a looser 10 percent scored better; with the full population the
faithful 5 percent wins, which is the sort of thing that only shows up if you
sweep both together."""

PROJECTION_SEED = 1987
"""The random claw assignment is drawn once and then frozen, because a fly does
not rewire its calyx between songs. 1987 is the year the song was released."""

# ── Dopamine and plasticity ──────────────────────────────────────────────────

W_BASELINE = 1.0
W_MAX = 2.0
W_MIN = 0.0
"""Kenyon cell to MBON synapses start at baseline and are bounded. Dopamine can
drive them to zero but not below."""

LEARNING_RATE = 0.02
RECOVERY_RATE = 0.0015
"""Dopamine-gated depression, and the slow drift back to baseline that makes
a fly memory fade. Both are per presentation, and they matter jointly: a
synapse settles where the depression it receives balances the recovery it
gets anyway, at ``w_baseline - learning_rate * p * d / recovery_rate`` for a
cell active a fraction ``p`` of the time under mean dopamine ``d``. That
ratio, not either rate alone, sets how hard the fly is allowed to commit."""

# ── Behaviour ────────────────────────────────────────────────────────────────

DA_TAU = 0.9
"""Seconds. Time constant of the dopamine pool that turns a stream of percepts
into one decision."""

DA_BASELINE = 0.66
"""Tonic level the evidence has to beat before the pool charges at all.

Dopaminergic neurons fire tonically and it is the phasic excursion above that
baseline that means anything. Without this term the pool only ever fills: a
seven-minute lecture contains some second that looks vaguely like a synth
stab, nothing ever drains, and the fly eventually gets excited about
everything. Subtracting a baseline turns the pool into an accumulator that
runs down on weak evidence, and it moved held-out track specificity from 0.57
to the figure quoted in the README."""

DA_SLOPE = 0.15
"""How sharply the pool's input saturates around the baseline.

Without saturation the drive is proportional to how far past the baseline the
evidence sits, and since a confident percept only sits a little past it, a
track the fly is sure about charges the pool at 40 percent of the rate total
certainty would. In practice the useful statistic is how *often* the fly says
yes, not by how much, and a saturating input curve measures exactly that. It
is also what neurons do."""

DA_STREAK_CONFIDENCE = 0.97
DA_STREAK_SECONDS = 0.60
"""A third way to commit, and the only one that does not care how long the
video is: six tenths of a second in which every consecutive percept is at or
above 0.97 confidence.

**The case this exists for.** Four seconds of the record stapled to the front
of an eleven-minute video. The pool cannot charge from four seconds inside six
hundred, and the burst above is switched off past twenty-five seconds by a gate
that exists for good reasons. So the most ordinary Rickroll there is -- the
sting hidden in something long -- was missed by construction, and said so in
its own documentation.

**Why a run, and not a longer mean.** The obvious fix is to ungate the burst.
It does not work, and the measurement is unambiguous: over a whole track the
best two-second mean confidence reaches 0.972 on *She Wants To Dance With Me*
and 0.985 on a TED talk, while a real eleven-minute video carrying four seconds
of the record scores 0.939. A mean over a window can be dragged up by one
spike, and a long video offers thousands of windows to find one in. Ranked by
that statistic the genuine Rickroll loses to a lecture about global ignorance.

An unbroken run of near-certainty is a different question, and a much harder
one to pass by accident. On the same full-length negatives only one of
forty-four holds 0.97 for six tenths of a second -- and it is *She Wants To
Dance With Me*, same artist, same producers, same year, which the fly is
already documented as partly confusing with the song.

**What it costs, measured on the out-of-fold tracks.** Nothing, and it pays:

    unheard upload      recall 1.000 -> 1.000   specificity 0.977 -> 0.977
    unheard rendition   recall 0.429 -> 0.619   specificity 0.909 -> 0.909

Both specificities are untouched; rendition recall -- the honest number, the
one for a cover the fly has never heard anyone play -- rises nineteen points,
because a cover that is right for half a second now counts even though its pool
never charges.

The bar is the tight end of a cliff. At 0.60 s upload specificity is 0.977; at
0.50 s it falls to 0.909. The video this was chased with holds 0.97 for 0.639 s,
which is a margin of six percent rather than the four thousandths that sank the
first version of the burst rule -- but it is still a margin, and it is recorded
here rather than buried.
"""

DA_BURST_SECONDS = 2.0
DA_BURST_CONFIDENCE = 0.90
DA_BURST_MAX_SECONDS = 25.0
"""A second, faster way to commit, for short recordings only: two seconds whose
mean confidence is at least 0.90, in a video of at most 25 seconds.

The pool above needs about ten seconds of the song to charge, which is correct
for a track and wrong for a meme. Most rickrolls in the wild are four to
fifteen seconds spliced onto the end of something else, and a fifteen-second
video ends with the pool at 0.47 against a threshold of 0.60 -- suspicious,
never convinced, and reported as "not a rickroll".

The pool needs roughly ten seconds of the song. That is right for a track and
wrong for a meme: most Rickrolls in the wild are a few seconds spliced onto the
end of something else, and a fifteen-second video ends with the pool at 0.47
against a threshold of 0.60 -- suspicious, never convinced, and reported as
"not a rickroll".

**Why the duration gate.** A sliding rule gets one chance to fire per percept,
so a four-minute track gives it nearly two thousand chances and a fifteen-second
clip about a hundred. Specificity therefore decays with length, measured on
out-of-fold negative clips at this setting:

     clip length   15 s    25 s    45 s    60 s   120 s
     specificity  96.3 %  95.1 %  93.4 %  92.4 %  90.0 %

Ungated, this path drops held-out upload specificity from 0.977 to 0.909 and
breaks the floor in training/train.py. Gated at 25 seconds it cannot touch a
full-length track at all, so the shipped figures -- upload 1.000 recall and
0.977 specificity, rendition 0.429 and 0.909 -- are exactly what they were, and
short videos get a rule held to the same 0.95 bar on their own population.

**What it buys.** On simulated memes -- filler, then four seconds of the record
-- recall goes from 39.8 percent with the pool alone to 67.5 percent. The
evaluation set had to be built, because every negative in the manifest is a
whole track and a rule aimed at fifteen-second memes had never met a
fifteen-second non-meme; roughly nine thousand negative clips were cut from the
out-of-fold timelines for it.

**Why 0.90 and not the 0.93 this shipped with.** The original cut was fitted
to one video that scored 0.934, a margin of four thousandths, and that was
recorded here as a caveat at the time. It was the right worry. Two ordinary
eight-second Rickrolls -- the shape the gate exists for -- score 0.9202 and
0.9269 over their best two seconds and were both reported as *not a rickroll*
while the fly was 97 percent confident about them.

`frrf-commitment` rebuilds the sweep, and the honest answer is that this
threshold is nearly free over a wide range. Every short clip the burst would
catch between 0.86 and 0.99, the pool already commits on by itself, so on nine
thousand out-of-fold short negatives the measured cost of coming down from 0.99
all the way to 0.86 is **zero** additional false alarms. They begin at 0.84,
which costs fifteen. 0.90 sits well inside the flat region and six hundredths
above the edge, rather than four thousandths above one example.

On real audio the change is surgical: the two eight-second clips now commit at
4.0 s, and every other cached video -- the record, the advert, the Astley hard
negative, three ordinary negatives and finding 6's own fifteen-second meme --
behaves exactly as before. The hard negative is the reason the gate is not
also up for negotiation: its best two seconds average 0.9479, above this cut,
and only its 207-second length keeps the burst away from it.

Loosely, two compartments with different kinetics: the fly's dopaminergic
neurons are not all slow, and a phasic path beside a tonic one is the sort of
thing the mushroom body has. That is an analogy, not a citation. The honest
description is that memes are short and the product has to notice them."""

DA_GAIN = 1.0
DA_COMMIT = 0.35
"""The fly commits once the pool crosses this fraction of full charge. Full
charge is what unbroken, total certainty would eventually produce, so 0.35
means roughly a third of the way to convinced. Everything the app calls
reaction time is measured against that crossing.

The tau, the baseline and this threshold are all chosen on out-of-fold traces
by training/train.py, not by hand."""


@dataclass(frozen=True)
class BrainConfig:
    """A complete parameter set, carried with the weights so a saved fly is
    reproducible even if the defaults above move.

    **The defaults above are starting points, not the shipped fly.** Training
    tunes the commitment parameters and saves what it chose into the model, so
    a trained `models/fly_brain.npz` carries `da_tau`, `da_baseline` and
    `da_commit` that differ from the module constants here. Anything measuring
    the fly's behaviour must take its config from the loaded model --
    `FlyBrain.load(...).config` -- and never from a bare `BrainConfig()`, which
    describes an untrained animal and will quietly produce different verdicts.
    """

    sample_rate: int = SAMPLE_RATE
    n_fft: int = N_FFT
    frame_hop: int = FRAME_HOP
    n_mel: int = N_MEL
    n_chroma: int = N_CHROMA
    chroma_n_fft: int = CHROMA_N_FFT
    chroma_tolerance_cents: float = CHROMA_TOLERANCE_CENTS
    mel_fmin: float = MEL_FMIN
    mel_fmax: float = MEL_FMAX
    chroma_fmin: float = CHROMA_FMIN
    chroma_fmax: float = CHROMA_FMAX
    subframe_frames: int = SUBFRAME_FRAMES
    subframes: int = SUBFRAMES
    window_hop_frames: int = WINDOW_HOP_FRAMES
    target_rms: float = TARGET_RMS

    al_exponent: float = AL_EXPONENT
    al_sigma: float = AL_SIGMA
    al_suppression: float = AL_SUPPRESSION
    al_rmax: float = AL_RMAX

    n_kenyon: int = N_KENYON
    n_claws: int = N_CLAWS
    kc_sparsity: float = KC_SPARSITY
    projection_seed: int = PROJECTION_SEED

    w_baseline: float = W_BASELINE
    w_max: float = W_MAX
    w_min: float = W_MIN
    learning_rate: float = LEARNING_RATE
    recovery_rate: float = RECOVERY_RATE

    da_tau: float = DA_TAU
    da_baseline: float = DA_BASELINE
    da_slope: float = DA_SLOPE
    da_gain: float = DA_GAIN
    da_commit: float = DA_COMMIT
    da_streak_confidence: float = DA_STREAK_CONFIDENCE
    da_streak_seconds: float = DA_STREAK_SECONDS
    da_burst_seconds: float = DA_BURST_SECONDS
    da_burst_confidence: float = DA_BURST_CONFIDENCE
    da_burst_max_seconds: float = DA_BURST_MAX_SECONDS

    compartments: tuple[str, ...] = field(default=("approach", "avoidance"))

    @property
    def channels_per_subframe(self) -> int:
        return self.n_mel + self.n_chroma

    @property
    def n_receptors(self) -> int:
        """Length of one percept as it leaves the ear."""
        return self.subframes * self.channels_per_subframe

    @property
    def window_frames(self) -> int:
        return self.subframes * self.subframe_frames

    @property
    def frames_per_second(self) -> float:
        return self.sample_rate / self.frame_hop

    @property
    def window_seconds(self) -> float:
        """True span of one percept, first sample to last.

        Not ``window_frames / frames_per_second``: the last frame reaches
        ``n_fft`` samples past its own start, so a percept covers a little
        more sound than its stride suggests.
        """
        return ((self.window_frames - 1) * self.frame_hop + self.n_fft) / self.sample_rate

    @property
    def window_hop_seconds(self) -> float:
        return self.window_hop_frames / self.frames_per_second

    @property
    def n_active_kenyon(self) -> int:
        return max(1, round(self.n_kenyon * self.kc_sparsity))

    def blocks(self) -> list[tuple[int, int]]:
        """Index ranges that share a gain-control pool.

        Mel bands and chroma bins are different units, so they normalise among
        their own kind, per sub-frame.
        """
        spans: list[tuple[int, int]] = []
        for s in range(self.subframes):
            base = s * self.channels_per_subframe
            spans.append((base, base + self.n_mel))
            spans.append((base + self.n_mel, base + self.channels_per_subframe))
        return spans

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> BrainConfig:
        known = {f for f in cls.__dataclass_fields__}
        cleaned = {k: v for k, v in raw.items() if k in known}
        if "compartments" in cleaned:
            cleaned["compartments"] = tuple(cleaned["compartments"])
        return cls(**cleaned)
