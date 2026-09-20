# FruitRickRollFly

A Drosophila mushroom body model that learns to release dopamine when it hears
a Rickroll.

Paste a YouTube link. It downloads the audio, runs it through a model of the
fruit fly's olfactory learning circuit — a sparse random expansion read out by
two output neurons, with dopamine as the only write signal — and shows you what
the fly's dopamine did about it, second by second.

The whole animal is 156 kB.

```
sound ──► Johnston's organ ──► antennal lobe ──► Kenyon cells ──► MBONs ──► dopamine pool ──► a verdict
          48 mel + 12 chroma   divisive gain    4,000 cells,     approach    leaky
          × 3 sub-frames       control          200 firing       avoidance   integrator
          = 180 receptors                       (5 %)
```

## Run it

```bash
uv sync --extra dev
uv pip install -e .

frrf-fetch                       # download the corpus and turn it into percepts
frrf-train                       # cross-validate, tune the commit rule, ship a fly
frrf-evaluate                    # draw what cross-validation found

cd web && npm install && npm run build && cd ..
uvicorn api.main:app             # API and frontend on one origin, one process
```

Training holds itself to a memory ceiling — 8 GB by default, `--memory-budget`
or `FRRF_MEMORY_BUDGET_GB` to move it. It projects its peak before starting,
refuses to run if that will not fit, and reports the measured peak at the end.
The real run uses about 1.1 GB.

## What it scores

Two questions get asked, and they are **not** the same question.

**Unheard rendition.** Hide every recording of one performance, train on the
rest, ask about what was hidden. Can it recognise the song when someone else
plays it?

**Unheard upload.** Hold out whole uploads of the 1987 master while other
uploads of that same master stay in training. This is leakage in the strict
sense and it is stated as such — it is also exactly what the application does,
because the link someone pastes is nearly always that record arriving as a
re-encode, a remaster or a lyric video.

| | percept AUC | track recall | track specificity | first suspicion | commits |
|---|---|---|---|---|---|
| **unheard rendition** | 0.704 macro · 0.780 pooled | 0.429 | 0.909 | 2.3 s | 28.1 s |
| **unheard upload** | 0.971 macro · 0.971 pooled | 1.000 | 0.977 | 0.8 s | 10.1 s |

There are two ways for the fly to commit. The dopamine pool is the normal one
and needs about ten seconds of the song. A meme does not have ten seconds — it
has four, spliced onto the end of a cat video — so a second path commits on two
seconds averaging 0.93 confidence, in recordings of at most 25 seconds. The
gate is what keeps it honest: it cannot reach a full-length track, so the
figures above are untouched by it. See finding 6 in
[docs/FINDINGS.md](docs/FINDINGS.md).

65 tracks, 66,035 percepts, 19,156 of them the song. Confidences are pooled
across folds, never valences: each fold trains its own output weights, so a
valence of 0.1 in one fold has no relation to a valence of 0.1 in another.

![ROC, pooled over every out-of-fold percept](docs/img/roc.png)

The macro figure hides a wide spread. Every upload fold is excellent; two
rendition folds are at or below chance.

![Per-fold AUC](docs/img/folds.png)

## Read the numbers honestly

**The headline is the upload number, and it contains leakage by construction.**
0.971 is what the deployed fly does when it has heard nine other uploads of the
same master. It is the right number for the product and the wrong number for
"does it know the song".

**The rendition number is the honest one, and it is 0.704.** For a piano cover
or a live performance the fly is much closer to guessing.

**Track-level figures carry a mild optimism.** The commit rule's three numbers
are chosen against the 65 out-of-fold tracks. The percept AUCs are untouched by
that.

**And the specificity is flattered.** Adding four ordinary uploads of "She
Wants To Dance With Me" — same artist, same producers, same year — drops the
best reachable upload specificity from 0.977 to 0.897, below the floor the
commit rule is held to. The fly has partly learned *Stock Aitken Waterman,
1987, that voice* rather than *this song*.

That measurement, and the four others around it, are written up in
**[docs/FINDINGS.md](docs/FINDINGS.md)**. The short version: more epochs will
not help, a different decision rule will not help, more hard negatives make it
worse, a longer percept window makes it much worse, and the constraint is that
the representation is anchored to the surface of one recording rather than to
the song.

![What the commit rule cost](docs/img/commitment.png)

## Layout

| | |
|---|---|
| `brain/` | the circuit — ear, gain control, calyx, output compartments, dopamine |
| `training/` | corpus, fetch, cross-validation, scoring, plots |
| `api/` | FastAPI app; SSE stream so the browser can watch a track play |
| `web/` | React frontend; the circuit in 3D on a three.js canvas, on one screen |
| `docs/BRAIN.md` | what is a fly and what is an engineering choice, number by number |
| `docs/FINDINGS.md` | what the measurements said, including the unwelcome parts |
| `models/` | the shipped fly, its metrics, and the out-of-fold traces |

The interface is one screen and does not scroll: the mushroom body turns in
the middle of it, 4,000 Kenyon cells as points inside the calyx with about 200
lit at any moment, the video beside it, and the whole response along the
bottom. The anatomy is drawn from the arrangement the textbooks describe
rather than measured from a connectome, and the page says so. It is also,
deliberately, a MySpace profile from 2003.

`models/traces.npz` holds every out-of-fold confidence timeline. Cross-validation
is the expensive part of this project and those timelines are its real product:
every figure and every commit-rule experiment is a function of them, so
re-asking a question of the model costs a file read rather than thirteen folds
of retraining.

## Develop

```bash
pytest          # 88 tests
ruff check .
```

## Credits

The architecture is Drosophila's. The parameters that are the fly's say so in
`brain/config.py`; the ones that are engineering say that too. The song is
Stock, Aitken and Waterman's, 1987.
