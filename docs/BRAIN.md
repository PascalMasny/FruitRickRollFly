# The circuit

What in here is a fly, what is an engineering choice, and how to tell them
apart. `brain/config.py` carries the numbers; this is the argument for them.

The claim the project makes is narrow and worth stating precisely: **this is a
model of the Drosophila mushroom body applied to audio, not a fly.** The
mushroom body is an associative memory whose architecture is unusually well
described — a sparse random expansion read out by a handful of output neurons,
with dopamine as the write signal — and that architecture is what is
reproduced. The ear in front of it is not a fly's ear, and the thing it learns
is not a smell.

## The signal path

```
sound ──► Johnston's organ ──► antennal lobe ──► Kenyon cells ──► MBONs ──► dopamine pool ──► a verdict
          48 mel + 12 chroma   divisive gain    4,000 cells,     approach    leaky
          × 3 sub-frames       control          200 firing       avoidance   integrator
          = 180 receptors                       (5 %)
```

Each stage below says what the fly has, what this model does, and which of the
two the number came from.

---

### 1. Johnston's organ — the ear

**The fly.** Drosophila hears with its antennae. Johnston's organ holds roughly
480 mechanosensory neurons in five functional groups, tuned to different
frequencies of antennal vibration. It is a real frequency analyser, and it is
how a fly hears a courtship song.

**The model.** A mel filterbank, 48 bands from 40 Hz to 8 kHz, read as
tonotopic channels. Three consecutive 255 ms sub-frames make one percept, so
the fly decides on 801 ms of sound — about one and a half beats at the target
song's 113 BPM.

**Where this departs from the animal.** The 12 chroma bins are *not* a fly
structure and are not pretended to be. They are pitch classes, and they exist
because harmony is what survives a piano cover when timbre does not. They get
their own longer transform (4096 points, 186 ms) because at the 1024-point
window the mel bands use, a bin is 21.5 Hz wide — three semitones at the bottom
of the bass range — and the pitch classes down there came out as noise.
Measured effect of that change on held-out renditions: AUC 0.802 → 0.828.

---

### 2. The antennal lobe — gain control

**The fly.** Olsen, Bhandawat & Wilson (2010) showed that projection neuron
output is a divisively normalised function of its input: each channel is
divided by what the whole population is doing. Odour concentration varies over
orders of magnitude and this is how the fly's representation survives it.

**The model.** The same divisive form, with the exponent from that paper. Mel
bands normalise against mel bands and pitch classes against pitch classes, one
pool per sub-frame, because they are different units and dividing an amplitude
by a quantity in different units means nothing.

**Engineering, not biology.** `al_sigma` and `al_suppression` are fitted to the
dynamic range of music rather than of odour. The per-channel `gains` are a
homeostatic scaling fitted once from the training corpus: low mel bands carry
far more energy than high ones in every recording ever made, and without it the
top of the spectrum would never win a Kenyon cell.

---

### 3. Kenyon cells — the sparse random expansion

**The fly.** This is the part the project exists for. Each Kenyon cell grows a
handful of dendritic claws, and each claw grabs one projection neuron
essentially at random. Nobody chooses which. Dasgupta, Stevens & Navlakha
(*Science*, 2017) showed this is a locality-sensitive hash in the formal sense:
similar input gives a similar set of winners. Then the APL neuron — one cell
innervating the whole lobe — feeds inhibition back and leaves only a few
percent firing. What comes out is a sparse binary tag: the fly's name for this
particular sound.

**The model.** 4,000 Kenyon cells, 20 claws each, 5 % left unsilenced.

**Provenance of each number.**

| Number | Value | Where it comes from |
|---|---|---|
| Kenyon cells | 4,000 | The connectome counts ~2,000 per hemisphere and a fly has two. This is one whole animal. Worth 0.03 AUC over one hemisphere — the best return of any parameter in the file, and the only one justified purely by "the fly really does have that many". |
| Claws per cell | 20 | The *ratio* is preserved, not the count. A fly grows ~6 claws from ~50 projection neurons, 12 %; this model's input layer is larger, and 20 of 180 is 11 %. Holding the absolute count at 6 costs 0.03 AUC, because 6 claws out of 180 see too little of a percept to say anything. |
| Sparsity | 5 % | Matches the measured sparseness of the real code. At 2,000 cells a looser 10 % scored better; with the full population the faithful 5 % wins — which only shows up if you sweep both together. |
| Projection seed | 1987 | The claw draw is frozen, because a fly does not rewire its calyx between songs. The year the song was released. |

**The least-evidenced step in the model.** Each cell gets its own firing
threshold, set so it wins about 5 % of the time on the training corpus.
Excitability homeostasis is well established in neurons generally; for Kenyon
cells specifically the evidence is thinner. It is here because the code quality
without it is measurably worse — claws are drawn at random, so some cells
sample six loud low-frequency channels and win every competition while others
never fire at all, and a code where the same 1,150 cells carry every sound is a
poor code.

---

### 4. MBON compartments — where the memory lives

**The fly.** The mushroom body lobes are cut into compartments, each with its
own output neuron and its own dopaminergic neurons. Each MBON pushes behaviour
one way: towards the thing or away from it. **Learning is subtraction.**
Dopamine released in a compartment depresses exactly those Kenyon cell synapses
that were active at the time, so an experienced smell stops driving the
response it used to drive. A memory is a pattern of weakened synapses and
nothing else.

**The model.** Two compartments, `approach` and `avoidance`. Weights start at
baseline, are bounded, and only ever move by depression and recovery. Valence
is approach minus avoidance.

**Why recovery matters.** Depression alone would floor every synapse at zero
within one pass over the corpus. The synapse settles where the depression it
receives balances the recovery it gets anyway — at
`w_baseline − learning_rate × p × d / recovery_rate` for a cell active a
fraction `p` of the time under mean dopamine `d`. That *ratio*, not either rate
alone, sets how hard the fly is allowed to commit. Recovery is applied per
presentation rather than per epoch, and compounded exactly rather than
linearly: a batch of a thousand presentations at 0.0015 would otherwise move a
synapse 150 % of the way to baseline and overshoot it.

---

### 5. Dopamine — two different jobs

Dopamine does two things here and they are genuinely not the same thing.

**During training it is a prediction error.** A fly does not release dopamine
because something good happened; it releases dopamine because something *better
than expected* happened. Felsenberg and colleagues showed this directly in
Drosophila in 2018: the same DANs that write a memory also revise it when the
prediction turns out wrong. Two clusters split the sign. PAM signals
better-than-expected and innervates the compartments whose MBONs drive
avoidance; PPL1 signals worse-than-expected and innervates the approach
compartments. Either way the synaptic effect is depression. That asymmetry is
the whole of the fly's valence system.

**During listening it is an accumulator.** One percept is 800 ms and the fly is
not asked to bet its life on it. The pool integrates evidence and the animal
commits when it crosses threshold; that crossing is what the app reports as
reaction time.

Two details in the accumulator are load-bearing:

- **The tonic baseline.** Dopaminergic neurons fire constantly and only the
  phasic excursion above that background carries a signal. Without the
  subtraction the pool only ever fills: a seven-minute lecture contains some
  second that looks vaguely like a synth stab, nothing ever drains, and the fly
  eventually gets excited about everything. Adding it moved held-out track
  specificity from 0.57 to the figure in the README.
- **The saturating input curve.** Without it, drive is proportional to how far
  past the baseline the evidence sits, and since a confident percept only sits
  a little past it, a track the fly is sure about charges the pool at 40 % of
  the rate total certainty would. The useful statistic is how *often* the fly
  says yes, not by how much — and a saturating curve measures exactly that. It
  is also what neurons do.

The time constant, the baseline and the threshold are **not learned**. They are
a decision rule, chosen by `training/train.py` on out-of-fold traces, and
choosing three numbers against the held-out tracks is a mild optimism that the
track-level figures carry and the percept AUCs do not.

---

## What this model is not

- **Not a fly's ear.** A fly cannot hear a pop song; Johnston's organ is used
  here as a frequency analyser because that is what it is, not because a fly
  would ever do this.
- **Not a fly's number of neurons anywhere but the calyx.** 180 receptors is
  not 480 sensory neurons, and two MBON compartments is not the ~34 the
  connectome describes.
- **Not online learning.** A real fly writes a memory in one trial. This one
  takes 60 epochs over a fixed corpus, because it is being asked to recognise a
  song across re-encodes rather than to remember a single episode.
- **Not a claim about how anything hears music.** It is a claim that a sparse
  random expansion with depression-only plasticity is enough to do this task,
  which is a claim about the architecture.

## Reading the numbers

`models/metrics.json` reports two questions that are not the same question, and
`frrf-evaluate` draws them. See the README for what they mean and which one to
believe for which purpose.
