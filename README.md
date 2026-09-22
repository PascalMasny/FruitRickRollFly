# FruitRickRollFly

A Drosophila mushroom body model that learns to release dopamine when it hears
a Rickroll.

Paste a link — YouTube, TikTok or Instagram. It downloads the audio, runs it through a model of the
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
frrf-meshes                      # optional: rebuild the neuropil surfaces (committed already)
frrf-train                       # cross-validate, tune the commit rule, ship a fly
frrf-evaluate                    # draw what cross-validation found
frrf-insights                    # draw what it was trained on, and write docs/TRAINING.md
frrf-corrections                 # fold hand-marked spans back into the corpus
frrf-watch                       # optional: fetch the corpus as video, for the eye
frrf-commitment                  # optional: re-sweep the commit rule on saved traces

cd web && npm install && npm run build && cd ..
FRRF_ADMIN=1 FRRF_DEV=1 uvicorn api.main:app    # one origin, one process
```

`FRRF_ADMIN=1` is what puts the workshop and the notes page there. They start
processes on this machine and write files to it, which is the point on a
laptop and is why they are off by default; see **Put it somewhere** below.

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
| **unheard rendition** | 0.704 macro · 0.780 pooled | 0.619 | 0.909 | 2.3 s | 41.9 s |
| **unheard upload** | 0.971 macro · 0.971 pooled | 1.000 | 0.977 | 0.8 s | 10.0 s |

There are **three** ways for the fly to commit, because a Rickroll comes in
three shapes.

The dopamine pool is the normal one and needs about ten seconds of the song.
A meme does not have ten seconds — it has four, spliced onto the end of a cat
video — so a second path commits on two seconds averaging 0.90 confidence, in
recordings of at most 25 seconds; an eight-second Rickroll commits at about
4 s. That gate is what keeps the second path honest, but it also meant the most
ordinary Rickroll of all was missed by construction: four seconds of the record
buried in eleven minutes of something else, far too long for the gate and far
too short for the pool.

So there is a third, and it is the only one that does not care how long the
video is: **six tenths of a second in which every consecutive percept is at or
above 0.97**. Ungating the second path instead does not work, and the
measurement is not close — over a whole track the best two-second mean reaches
0.972 on *She Wants To Dance With Me* and 0.985 on a TED talk, while a real
eleven-minute video carrying four seconds of the record scores 0.939. A mean
can be carried by one spike and a long video supplies thousands of windows to
find one in; an unbroken run cannot. It costs neither specificity above, and it
is why rendition recall is 0.619 rather than 0.429. See finding 6 in
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

**Track-level figures carry a mild optimism.** The commit rule's numbers are
chosen against the 65 out-of-fold tracks. The percept AUCs are untouched by
that.

**Catching more covers made the fly slower to say so.** Rendition recall went
from 0.429 to 0.619 when the third path was added, and the median commit time
went from 28.1 s to 41.9 s with it. Nothing got slower: the covers that were
already caught are caught at the same moment as before. The ones that are new
are the hard ones, and they are caught late.

**And the specificity is flattered.** Adding four ordinary uploads of "She
Wants To Dance With Me" — same artist, same producers, same year — drops the
best reachable upload specificity from 0.977 to 0.897, below the floor the
commit rule is held to. The fly has partly learned *Stock Aitken Waterman,
1987, that voice* rather than *this song*.

That measurement, and the others around it, are written up in
**[docs/FINDINGS.md](docs/FINDINGS.md)**, and the corpus underneath them —
what it contains, and what the fly makes of every single track — is drawn in
**[docs/TRAINING.md](docs/TRAINING.md)**. The short version: more epochs will
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
| `web/` | React frontend; real hemibrain neuropils in three.js, on one screen |
| `training/meshes.py` | pulls those neuropils out of the hemibrain; a build step, not a runtime one |
| `brain/eye.py` | a visual pathway: ommatidia, correlators, wide-field cells. Measured, and not shipped — see finding 7 |
| `training/corrections.py` | folds hand-marked spans back into training data |
| `docs/BRAIN.md` | what is a fly and what is an engineering choice, number by number |
| `docs/FINDINGS.md` | what the measurements said, including the unwelcome parts |
| `docs/TRAINING.md` | what the fly was trained on, drawn: the corpus, every track's spread, and sound against sight |
| `models/` | the shipped fly, its metrics, and the out-of-fold traces |

The interface is one screen and does not scroll: four panels, being the four
things worth looking at at once — the cells, the video, the numbers, and the
animal. That last one is a fly sitting in front of a monitor watching whatever
was pasted in, on a texture of the very same `<video>` element the panel above
plays, so the two can never drift apart. It leans towards the screen as the
dopamine pool fills, and its wings only go once it has committed — a fly that
is merely suspicious sits there.

The cells panel holds the 4,000 Kenyon cells inside a wireframe of the whole
brain — a central mass with an enormous eye either side — because a cluster of
dots on its own could be anything, and inside that outline it is visibly a
calyx in one hemisphere of a fly's head. The calyx is drawn a little
stronger than its surroundings, because the Kenyon cells sit at the brain's
dorsal surface where there is least tissue in front of them and against a
perfectly uniform haze they read as floating on top of the brain rather than
sitting inside it. The outline is the real hemibrain neuropils, drawn as soft translucent
volumes so the tissue accumulates where it is deep; the hemibrain is a partial volume, so the whole thing is mirrored
across the midline, and being a reflection rather than a measurement it is
only ever drawn as an outline. Otherwise the panel is the cells and nothing else — no neuropil surfaces, no receptors, no
labels on an organ. What is worth watching was never the envelope: it is that
about two hundred cells are firing at any instant and that which two hundred
changes completely as the song moves. Each cell keeps a short tail after it
stops firing, because at eight percepts a second an honest on/off reads as
flicker and hides exactly that turnover.

The positions are real. They were sampled inside the **Janelia FlyEM hemibrain
v1.2** calyx surface and rejected against the mesh, so the cloud is the shape
of the place these cells actually sit even with the surface no longer drawn.
`frrf-meshes` regenerates them; the neuropil GLB it also writes is kept in
`models/` as provenance rather than shipped to a browser that would download
half a megabyte and never use it.

## Telling it when it is wrong

The page has four tabs. **the fly** is the live one above. **training data**
is the corpus, interactively: every track's out-of-fold confidence as a
5th-to-95th spread, filterable down to the ones it missed and the ones it
false-alarmed on, which is the fastest way to see what it actually confuses.
**workshop** is where the flies live: which model answers for which sense,
and buttons to run the training commands with the log streaming back.
**notes** is a page to write on, saved to `data/notes.md` so it survives a
restart and can be committed next to the code it is about.

The workshop starts processes on the machine the server runs on, so the job
names are a fixed set and their arguments are built from templates on the
server. Nothing the page sends is concatenated into a command, the model name
is matched against a pattern that cannot contain a separator, and there is no
shell anywhere in the path. It is a local tool and it says so.

When the fly gets a video wrong, drag across the response strip to mark where
the song really is and say which it was. That lands in
`data/corrections.jsonl` as an append-only log — append-only because the
history of what was said about a video is itself worth keeping — and
`frrf-corrections` turns each span into cached percepts and writes a merged
manifest:

```bash
frrf-corrections
frrf-train --manifest data/manifest-with-corrections.json
```

Each correction is its own fold group, keyed on the video it came from, so two
spans of one video can never be split across a fold boundary. These are the
most useful labels the project can get: nobody bothers to correct a case the
fly already handles, so every one of them is out of distribution by
definition.

The verdict does not wait for the picture. The fly needs the audio and nothing
else, so the audio is fetched first — in the same call that returns the title,
rather than a second round trip for it — and the video downloads behind the
analysis. Pasting a link to a verdict is about 1.9 s cold, of which the model
is 0.2 s; it was 4 s when the pictures came first.

The video plays from our own copy rather than from a YouTube embed. The
uploads most worth asking about are very often the ones whose uploader has
disabled embedding, and for those the embed is a grey box reading *this video
is not available*; the file the fly listened to is already on disk, so it is
served from there. Links are YouTube, TikTok or Instagram, and nothing else:
which platforms count is a product decision and it lives in
`api/services/sources.py`, one source to a definition — its hosts, the shape of
its ids, and the way back to a canonical URL. A link shortener is followed —
a Rickroll is very often hidden behind one — but the rule after the redirect is
the rule before it, and every hop has to land on a shortener or on a source we
accept, so it cannot be pointed at anything else. Each platform's own share
link — `vm.tiktok.com`, `tiktok.com/t/`, `instagram.com/share/` — is followed
the same way, because it carries no id that can be read off the URL.

**Instagram needs credentials and YouTube will eventually.** Instagram returns
an empty media response to anyone who is not logged in, so it does not work at
all without a cookie jar; YouTube blocks datacenter address ranges, so it stops
working the moment this leaves a laptop. Both take the same answer: point
`FRRF_COOKIES_FILE` at a Netscape-format cookie file. Treat it as the
credential it is — whoever holds it is logged in as that account — and use an
account you are willing to lose.

`models/traces.npz` holds every out-of-fold confidence timeline. Cross-validation
is the expensive part of this project and those timelines are its real product:
every figure and every commit-rule experiment is a function of them, so
re-asking a question of the model costs a file read rather than thirteen folds
of retraining.

## Put it somewhere

```bash
docker compose up -d --build       # after pointing Caddyfile at your domain
```

Two stages: node builds the frontend, then a `python:3.13-slim` that carries
ffmpeg, the trained fly, and nothing from `data/`. Caddy terminates TLS in
front of it. `data/` is a volume; `models/` comes from the image, so a deploy
ships a fly rather than hoping one is on the disk.

**One worker, and it is not a default worth changing.** The analysis jobs, the
training runs, the rate-limit window and the caches in front of the model all
live in one process's memory. A second worker sees none of them and answers
half the event streams with a 404. Scaling out means moving that state
somewhere shared first.

What changes between a laptop and a public address is a set of environment
variables, and every default below is the safe reading:

| | default | |
|---|---|---|
| `FRRF_ADMIN` | `0` | Whether the workshop and the notes page are registered at all. They start processes on the host. |
| `FRRF_DEV` | `0` | Serves `/docs` and the schema, and lets Vite's origin through CORS. |
| `FRRF_MAX_VIDEO_SECONDS` | `1200` | Refused before the download, by yt-dlp, and again at decode by ffmpeg. |
| `FRRF_MAX_CONCURRENT_ANALYSES` | `2` | Analyses in flight. The rest wait in `queued`. |
| `FRRF_CACHE_BUDGET_GB` | `5` | `data/cache` is swept to this, oldest first. |
| `FRRF_RATE_PER_MINUTE` | `10` | Per client, on the two endpoints that cost something. |
| `FRRF_COOKIES_FILE` | unset | Netscape cookie jar for yt-dlp. Instagram does not work without one; YouTube will not from a datacenter. |
| `FRRF_BEHIND_PROXY` | `0` | Trust the first hop of `X-Forwarded-For`. Only true where a proxy really is in front. |
| `FRRF_TRUSTED_HOSTS` | unset | Comma-separated `Host` allowlist. |
| `FRRF_CORS_ORIGINS` | unset | Comma-separated. Empty in production: the frontend is served from this same origin. |

The workshop is not something to put on a public interface behind a password.
Leave `FRRF_ADMIN=0`, publish nothing, and reach it down an SSH tunnel when
you want it:

```bash
ssh -L 8000:127.0.0.1:8000 you@host
```

**The thing most likely to break this is not in this repository.** YouTube
blocks datacenter address ranges, and every major host is one. Expect
`Sign in to confirm you're not a bot` and plan for it before anything else: a
cookies file, a PO-token provider, or egress that is not a datacenter. A
commercial VPN is not a fix -- those exit through datacenter ranges too, ones
that have been used for exactly this for years. And yt-dlp goes stale within
weeks of a YouTube change, so rebuild on a schedule rather than pinning it and
forgetting.

## Develop

```bash
pytest          # 180 tests
ruff check .
```

## Credits

The architecture is Drosophila's. The parameters that are the fly's say so in
`brain/config.py`; the ones that are engineering say that too. The song is
Stock, Aitken and Waterman's, 1987.

The neuropil surfaces in `models/fly-brain.glb`, and the Kenyon cell positions
in `web/public/kenyon-cells.bin` sampled inside the calyx of them, are from the
[Janelia FlyEM
hemibrain](https://www.janelia.org/project-team/flyem/hemibrain) v1.2 ROI
segmentation, used under CC BY 4.0. They are the only part of this repository
that is someone else's measurement rather than our arithmetic.
