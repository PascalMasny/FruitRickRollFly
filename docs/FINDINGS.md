# What the measurements actually said

Four questions were asked of the trained fly. Three of them came back "no",
and the "no"s are more useful than the "yes" was.

---

## 1. Would more training help? No.

Rendition track recall is 0.429 — the fly commits to 9 of the 21 held-out
positives. The obvious reading is that it needs more epochs.

It does not. Every one of the twelve misses peaks well above one half:

| held-out positive | peak confidence |
|---|---|
| studio-1987 (×5 uploads) | 0.99 |
| tv-countdown-1987 | 0.98 |
| live-bbc-nye | 0.97 |
| pianoforte (×2) | 0.96, 0.94 |
| live-2016 | 0.92 |
| live-late-late-show | 0.90 |
| live-foo-fighters | 0.88 |

Mean peak confidence across the misses is **0.96**. The circuit recognises
these tracks percept by percept; what fails is the dopamine pool on top of it,
which never crosses its threshold. More epochs cannot move a threshold.

`docs/img/misses.png` draws this: the pale line is what the circuit believed,
the solid line is the pool, the dashed line is the bar it had to clear.

## 2. Would a different commit rule help? No.

The commit rule is a leaky integrator with three free numbers — time constant,
tonic baseline, threshold — swept over 252 combinations. An obvious suspicion
is that the *shape* is wrong, not the numbers.

A second family was tested on the same out-of-fold traces: **N of the last M
percepts above a cut**, 210 combinations, a rate rule rather than an integrator.
Under identical constraints:

| rule family | best rendition recall | at upload specificity |
|---|---|---|
| leaky integrator (current) | **0.429** | 0.977 |
| N-of-M | 0.238 | 0.955 |

The integrator wins, and it wins comfortably. `docs/img/commitment.png` shows
the further point: among the rules that clear the specificity floor, the one
already chosen has the highest rendition recall of any of them. The tuner is
not leaving anything on the table.

## 3. So what *is* the constraint? Three false positives.

The rule is held to 0.95 specificity on held-out uploads before recall is even
looked at. Four negatives trip it, and three are the same artist:

```
astley-whenever    Rick Astley - Whenever You Need Somebody         at  9.5s
astley-whenever    Rick Astley - Whenever You Need Somebody (JP)    at  9.5s
astley-she-wants   Rick Astley - She Wants To Dance With Me         at 64.1s
speech-ted         TED - How not to be ignorant about the world     at 12.0s
```

Re-running the sweep with the Rick Astley negatives removed:

| | best rendition recall |
|---|---|
| as measured | 0.429 |
| without the Astley negatives | **0.762** |

Those three tracks cost **0.333 of rendition recall**. The fly had partly
learned *Stock Aitken Waterman, 1987, that voice* rather than *this song*.

## 4. Would more hard negatives fix it? No — and this is the important one.

The corpus already carried 19 hard negatives: nine Rick Astley singles, six
other Stock Aitken Waterman productions, and a different song that happens to
share the title. Fourteen more were added — four further uploads each of the
two tracks the fly was measured confusing with the target, plus Mel & Kim,
Sinitta, Jason Donovan and Kylie Minogue.

**Training failed.** No commit rule in the sweep reaches the 0.95 specificity
floor any more; the best reachable is **0.897**.

Ranking every negative by the fraction of its percepts the fly scores above
one half:

| track | over 0.5 | |
|---|---|---|
| She Wants To Dance With Me (HQ) | **99.2 %** | new |
| She Wants To Dance With Me (2023 remaster) | 91.5 % | new |
| She Wants To Dance With Me (music video) | 89.5 % | new |
| She Wants To Dance With Me (Top Of The Pops) | 89.2 % | new |
| *best actual positive (karaoke)* | *88.3 %* | |
| She Wants To Dance With Me (original entry) | 70.4 % | |
| *median actual positive* | *50.4 %* | |

The fly is **more confident that "She Wants To Dance With Me" is the Rickroll
than it is about any real Rickroll in the corpus.**

This was checked for the obvious mistake first. A negative that secretly
contains the target would poison training, and the curation rules say so. It is
not that: all four new uploads run 196–199 s against the single's 3 min 19,
none is a compilation, and the pre-existing entry for the same song is the
atypical one — 259 s, sixty seconds longer than the others.

The conclusion is unwelcome and worth stating plainly: **the 0.977 specificity
the model reports was flattered by thin coverage of its nearest confusable
neighbour.** One upload of "She Wants To Dance With Me" was in the corpus, and
it happened to be an unusual one. With four ordinary uploads of it, the model's
real discrimination shows, and it is much worse.

Those fourteen tracks are carried in the manifest at `use: "holdout"`. They are
fetched and reproducible but not trained on, because adopting them means
lowering the specificity floor, and that floor is a product promise rather than
a hyperparameter.

---

## 5. Would a longer percept fix it? No — and it costs most of the recall.

The obvious reading of finding 4 is that 801 ms is too short: over a beat and a
half, two Stock Aitken Waterman singles are nearly the same object, and what
separates them is melody and harmonic movement. So the window was doubled —
`subframes` 3 → 6, a 1.567 s percept, about three beats. The claws went 20 → 40
with it, because the receptor layer doubled and the config's own argument is
that the *ratio* is what carries the hash; leaving them at 20 would have halved
the sampling ratio to 5.6 % and confounded the two changes.

Percept-level, it is a wash. Track-level, it is a disaster.

| | 0.801 s | 1.567 s |
|---|---|---|
| rendition macro AUC | 0.7038 | 0.7014 |
| rendition pooled AUC | 0.7804 | 0.7627 |
| **rendition track recall** | **0.429** | **0.095** |
| rendition track specificity | 0.909 | 0.932 |
| upload macro AUC | 0.9714 | 0.9756 |
| upload track recall / specificity | 1.000 / 0.977 | 1.000 / 0.977 |
| first suspicion (upload) | 0.8 s | 2.6 s |

**Held-out positives caught: 9 of 21 → 2 of 21.** The only two that survive are
`extended-mix` and `karaoke`.

And on the hard corpus it does not help at all: the best reachable upload
specificity goes **0.897 → 0.879**, slightly worse than the short window.

The per-fold table says why, and it is not noise — the folds move in opposite
directions, consistently:

| rendition fold | 0.801 s | 1.567 s | |
|---|---|---|---|
| live-foo-fighters | 0.752 | **0.857** | up |
| live-bbc-nye | 0.703 | **0.774** | up |
| karaoke | 0.891 | **0.933** | up |
| extended-mix | 0.939 | **0.957** | up |
| studio-1987 | **0.903** | 0.879 | down |
| tv-countdown-1987 | **0.656** | 0.578 | down |
| pianoforte | **0.467** | 0.369 | down |
| live-2016 | **0.329** | 0.262 | down |

The interpretation that fits: **a longer window is more rigid about tempo.**
Three beats of a performance recorded at a slightly different tempo drift out
of alignment with what the fly learned; a beat and a half drifts half as far.
The wider percept is a better template for *the same recording* — every upload
fold improved, and upload AUC went up — and a worse one for *a different
performance of the same song*, which is the thing that was supposed to get
better.

That is the opposite of the intended effect, so the change was reverted. It is
written down here because it is a cheap experiment to repeat by accident.

It also rules out the framing. The problem is not that the window is too short
to contain the melody. Tempo-rigidity and timbre-confusion are the same
complaint from two directions: the representation is anchored to the *surface*
of a specific recording rather than to what the song is. Lengthening the window
moves it further in that direction, not less.

---

## 6. The meme case: the pool is the wrong shape for a four-second sting

A real meme, pasted in: `hB7CDrVnNCs`, fifteen seconds long, the record spliced
in from 11 s to 15 s. The app said **not a rickroll**, and it was not close to
random about it:

```
first suspicion  10.89 s      peak confidence  0.965
peak dopamine     0.474   vs   threshold  0.60
```

It ran out of video at 79 percent of the way to convinced. The pool needs about
ten seconds of the song; the meme carried four. This is not a rare shape — most
Rickrolls in the wild are the first five to fifteen seconds of the record
stapled to the end of something else.

**A second commit path was added for it**: two seconds whose mean confidence is
at least 0.93, in a recording of at most 25 seconds. Three things made it
defensible.

*The evaluation set had to be built.* Every negative in the manifest is a whole
track, so a rule aimed at fifteen-second memes had never met a fifteen-second
non-meme. Roughly nine thousand short negative clips were cut from the
out-of-fold timelines, and memes were simulated the way memes are made: filler,
then a few seconds of the record.

*Specificity decays with length, and that is the whole argument for the gate.*
A sliding rule gets a chance to fire per percept, so a four-minute track gives
it nearly two thousand chances and a fifteen-second clip about a hundred:

| clip length | 15 s | 25 s | 45 s | 60 s | 120 s |
|---|---|---|---|---|---|
| specificity | 96.3 % | 95.1 % | 93.4 % | 92.4 % | 90.0 % |

Ungated, this path drops held-out upload specificity from 0.977 to 0.909 and
breaks the floor. Gated at 25 s it cannot reach a full-length track at all, so
every headline figure is unchanged — upload 1.000 / 0.977, rendition 0.429 /
0.909, still all committed through the pool — while short videos get a rule
held to the same 0.95 bar on their own population.

*What it buys.* On simulated four-second stings, recall goes from **39.8 % to
67.5 %**. End to end, the video above now commits at 13.7 s, and the record,
the advert, the ordinary negative and the Astley hard negative all behave
exactly as before.

Two caveats, recorded rather than buried. The threshold is 0.93 and that video
scores 0.934 over its best two seconds — a margin of four thousandths, which
means the cut is fitted to that one example as much as to the sweep. And a long
video with a short sting is still missed by construction: the gate is a
statement that a four-minute upload gets judged by the pool, whatever is
spliced into it.

### 6b. The first caveat came true, and the sweep was not reproducible

Two ordinary eight-second Rickrolls — *Rick Roll (Different link + no ads)* and
*Rick roll, but with different link*, the exact shape this rule exists for —
score **0.9202** and **0.9269** over their best two seconds. Both were reported
as *not a rickroll* while the fly was 97 percent confident about them and the
pool had stalled at 0.39 against 0.60. A threshold fitted four thousandths
above one example missed the next two examples it met.

Worse, the sweep that produced 0.93 was never committed, so the number could
not be argued with. `frrf-commitment` now rebuilds it from `models/traces.npz`:
memes cut as filler-then-sting from the **upload** family, short negatives cut
from ordinary tracks at the same lengths.

Rebuilding it turned up something the original write-up got wrong. **The burst
path barely fires at all.** Swept from 0.99 down to 0.86 against nine thousand
out-of-fold short negatives, the measured cost is *zero* additional false
alarms at every step — because every short clip the burst would catch, the pool
has already committed on by itself. False alarms begin at 0.84, where fifteen
appear. The claimed lift from 39.8 to 67.5 percent recall does not reproduce;
on this population the pool alone takes 95 to 100 percent of simulated memes,
and the burst's real job is the narrow band the pool stalls in — which is
exactly where those two videos sat.

So the cut moved to **0.90**: six hundredths above the edge of the flat region
rather than four thousandths above one example. On real audio the change is
surgical.

| video | before | after |
|---|---|---|
| Rick Roll, no ads (8 s) | never | **4.0 s** |
| Rick roll, different link (7 s) | never | **4.0 s** |
| Send this to all your friends (15 s) | 13.7 s | 13.1 s |
| the record (213 s) | 9.5 s | 9.5 s |
| insurance advert (65 s) | 4.6 s | 4.6 s |
| Astley hard negative (208 s) | never | never |
| three ordinary negatives | never | never |

The hard negative is why the 25-second gate is not also up for negotiation: its
best two seconds average **0.9479**, comfortably above the new cut, and only
its length keeps the burst away from it.

One case is still missed and stays missed: *10 rickrolls 1 video*, 34 seconds,
outside the gate, with a best two seconds of only 0.855. The gate remains a
statement that anything past 25 seconds is the pool's business.

Two measurements worth recording while the sweep existed. Short-clip
specificity is **0.86**, far below the 0.977 the fly holds on whole tracks —
fifteen percent of random five-to-twenty-five second windows of ordinary
negatives commit, through the pool, with the burst disabled entirely. That is a
pre-existing weakness of the pool on short inputs and nothing to do with this
rule. And the family a meme's sting is cut from changes the answer completely:
cut from `rendition`, simulated memes are so hard that nothing fires; cut from
`upload`, the pool takes almost all of them. Somebody pasting a Rickroll link
is pasting an upload, so `upload` is the population, and saying so is part of
the claim.

### 6c. The gate was the wrong variable, and the statistic was the wrong statistic

The caveat at the end of finding 6 — *a long video with a short sting is still
missed by construction* — is not a corner case. It is the most common shape a
Rickroll takes: four seconds of the record buried in ten minutes of something
else. Pasted in: an eleven-minute video containing **1.3 s and 1.4 s** of the
song. Peak confidence 0.976, pool stalled at 0.471 against 0.60, burst switched
off by the 25-second gate. **Not a rickroll.**

The obvious fix is to ungate the burst. It does not work, and the measurement
is not close. Best two-second mean confidence, over whole tracks, no gate:

| | best 2 s mean |
|---|---|
| TED talk, *How not to be ignorant about the world* | **0.985** |
| *She Wants To Dance With Me* (the hard negative) | **0.972** |
| the eleven-minute video that really is a Rickroll | 0.939 |

Ranked by that statistic the genuine Rickroll loses to a lecture. A mean over a
window can be carried by a single spike, and a long video offers thousands of
windows to find a spike in. The gate was not protecting an arbitrary length
limit; it was protecting a statistic that cannot survive many chances.

**An unbroken run can.** Requiring every consecutive percept to clear a high
bar is a much harder test to pass by accident, because it has to survive each
percept it covers rather than average over them. Of forty-four full-length
negatives, exactly one holds 0.97 for six tenths of a second — and it is *She
Wants To Dance With Me*, which this project already documents the fly as partly
confusing with the song.

So a third path, ungated: **0.97 held for 0.60 s**. Measured on the out-of-fold
tracks:

| | recall | specificity |
|---|---|---|
| unheard upload | 1.000 → 1.000 | 0.977 → **0.977** |
| unheard rendition | 0.429 → **0.619** | 0.909 → **0.909** |

Neither specificity moves. Rendition recall — the honest number — rises
nineteen points, because a cover that is briefly right now counts even though
its pool never charges. The eleven-minute video commits at 163.8 s, on the
song's second appearance.

Three things recorded rather than buried. The bar sits on a cliff: at 0.60 s
upload specificity is 0.977, at 0.50 s it is 0.909, and the video this was
chased with holds 0.97 for 0.639 s — a margin of six percent, better than the
four thousandths that sank the first burst rule, but still a margin. The new
recall is slower: median rendition commit goes from 28.1 s to 41.9 s and p90
from 50.6 s to 190.5 s, because nothing already caught got faster and
everything newly caught is hard and late. And *10 rickrolls 1 video*, 34
seconds, is still missed — its best run never holds 0.97 that long.

### 6d. The defaults in `brain/config.py` are not the shipped fly

Found while measuring the above, and worth more than a footnote. Training tunes
the commitment parameters and saves what it chose into the model, so:

| | `brain/config.py` | `models/fly_brain.npz` |
|---|---|---|
| `da_tau` | 0.9 | **2.0** |
| `da_baseline` | 0.66 | **0.72** |
| `da_commit` | 0.35 | **0.6** |

This is by design — the dataclass docstring says the config travels with the
weights — but it is a trap for anything that measures behaviour. A sweep built
on a bare `BrainConfig()` reproduces upload specificity of **0.614** where the
shipped fly scores **0.977**, and every conclusion drawn from it is about an
animal that was never shipped. The earlier short-clip numbers in 6b were
computed that way and should be read as indicative only; the real-audio table
in 6b was not, and stands. `BrainConfig`'s docstring now says this outright:
take the config from `FlyBrain.load(...).config`, never from the defaults.

## 7. The fly can watch, and it does not help

The question was whether the fly could be made to *see* the video rather than
only hear it. The answer is that the pathway works, the biology is sound, and
the fly learns almost nothing from it.

**What was built.** A Drosophila eye is about 750 ommatidia, so a frame becomes
a 32x24 hexagonal picture and no amount of wanting will get a face out of it.
What flies are extraordinary at is time -- flicker fusion near 200 Hz against
our sixty -- so the pathway is a motion pathway, and the textbook one:
ommatidia feed Reichardt correlators (a delayed signal from one facet
multiplied by its neighbour's undelayed one, minus the mirror of that product),
and those are pooled into twelve wide-field tangential cells standing in for
the lobula plate. Twelve fields, four directions each, plus twelve flicker
channels, is sixty a frame -- the ear's number on purpose, so three sub-frames
makes 180 receptors either way and the same calyx reads either sense.

**What it scored.** Pooled out-of-fold percept AUC, same folds, same circuit,
same everything but the sense:

| | rendition | unheard upload |
|---|---|---|
| ear | **0.780** | **0.971** |
| eye | 0.621 | 0.631 |

Above a coin flip, and nowhere near enough. `frrf-train` **refused to ship a
visual fly at all**: no commit rule reaches even a 0.70 specificity floor at
full upload recall, which is the trainer's own guard working exactly as
intended. `models/fly_eye.npz` does not exist and the application is unchanged.

**Two things the attempt turned up that were worth the trip.**

*A great many uploads are photographs.* Thirty-eight percent of the positives
in this corpus are a still cover image with the audio behind it, against
sixteen percent of the negatives -- so in this corpus **being a still image is
correlated with being the target**, P(positive | static) = 0.53 against a base
rate of 0.32. Normalising each video by its own peak activity turned those
photographs' compression shimmer into something that looked like choreography,
and the circuit could have learned that correlation and scored for it. It is a
fact about how the corpus was collected, not about the song. The eye now gates
on how confident it is that anything moved at all, and a photograph reads
0.00000 where a music video reads 0.03.

*Training a second sense found a silent corruption in the first.* `load_times`
read the default feature directory whatever `load_corpus` had been given, so
training on sight paired the eye's confidences with the ear's clock. It
happened to crash here because the two have different percept counts. Had they
matched, it would have produced a plausible, entirely wrong model in silence.

**Why it does not work, as far as the measurement shows.** The motion
statistics of a 1987 pop video are not very different from the motion
statistics of other pop videos, at twelve wide-field channels and thirty frames
a second. The one fold that does well -- extended-mix, AUC 0.948 -- is a
visualiser with distinctive strobing, which is the pathway recognising an
upload rather than the song. That is the same failure the ear has, and vision
makes it worse: a piano cover contains no Rick Astley at all, so sight cannot
help the rendition case, which is the one that is actually weak.

Kept anyway: `brain/eye.py`, `frrf-watch`, and `models/traces-eye.npz`, because
the negative result is only worth having if the evidence for it is re-readable.

---

## What this points at

Not more data, and not a better decision rule. The representation.

The percept is 801 ms of 48 mel bands and 12 pitch classes. Over that window,
two Stock Aitken Waterman singles cut in the same studio in the same year with
the same singer are nearly the same object — same tempo range, same drum
machine, same synth patches, same voice. What separates them is melody and
harmonic progression, which needs either more weight on the chroma channel or a
longer window than one and a half beats.

Three experiments follow from this, none of which needs new audio:

1. ~~**A longer percept.**~~ Tried, in finding 5. It makes the fly a better
   template-matcher for one recording and a worse recogniser of the song.
2. **Chroma against mel** — now the leading candidate. The gain control already
   normalises the two banks separately, so they can be re-weighted without
   touching the ear. Training a chroma-only and a mel-only fly would say
   directly which bank carries the Astley confusion. The expectation from
   finding 5 is that mel — timbre, production, the surface of the recording —
   is doing most of the work, and that is exactly the part two singles cut in
   the same studio in the same year have in common.
3. **Tempo invariance.** Finding 5 showed the representation is anchored to a
   tempo. Nothing in the model normalises for it. Sub-frames of a fixed number
   of *frames* could instead be a fixed number of *beats*, which is a real
   change to the ear and the biggest single idea left on the list.
4. **Adopting the harder corpus with an honest floor.** Train on all 79 tracks
   with `--with-holdout --min-specificity 0.85` and report the lower numbers, on
   the grounds that they are the true ones.

Reproducing any of the measurements above needs only `models/traces.npz` —
the out-of-fold confidence timelines — and no retraining.
