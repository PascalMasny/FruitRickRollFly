# The whole animal in one image: a built frontend, a NumPy circuit, and the
# two binaries it shells out to.
#
# Two things are easy to get wrong here and both are fatal rather than noisy.
# ffmpeg and ffprobe have to exist, because brain/audio.py, brain/eye.py and
# youtube.has_video_stream are all subprocess calls to them. And models/*.npz
# has to be in the image, because the server refuses to answer without a
# trained fly and /api/health says so.

# ── the frontend ─────────────────────────────────────────────────────────────
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ── the animal ───────────────────────────────────────────────────────────────
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies ahead of source, so editing a file does not reinstall NumPy.
# The stub packages exist only so hatchling can build a wheel to hang the
# editable install off; the real ones are copied over them below.
COPY pyproject.toml README.md ./
RUN mkdir -p brain api training \
    && touch brain/__init__.py api/__init__.py training/__init__.py \
    && pip install --no-cache-dir -e .

# Editable rather than installed, and deliberately: every path in this project
# is resolved relative to its own __file__, so a copy living in site-packages
# would look for models/ and data/ beside site-packages and find neither.
COPY brain/ ./brain/
COPY api/ ./api/
COPY training/ ./training/
COPY models/*.npz models/metrics.json ./models/
COPY --from=web /web/dist ./web/dist

# Owned by the runtime user before the volume lands on it: yt-dlp writes here,
# and a root-owned data/ is a container that starts and then cannot download.
RUN mkdir -p data/cache data/audio data/features data/features-eye data/video \
    && useradd --uid 10001 --create-home fly \
    && chown -R fly:fly /app
USER fly

# The safe reading of every one of these. A host that wants the workshop says
# so out loud, in its compose file, where it can be read back later.
ENV FRRF_ADMIN=0 \
    FRRF_DEV=0 \
    FRRF_BEHIND_PROXY=1 \
    FRRF_MAX_VIDEO_SECONDS=1200 \
    FRRF_MAX_CONCURRENT_ANALYSES=2 \
    FRRF_CACHE_BUDGET_GB=5 \
    FRRF_RATE_PER_MINUTE=10 \
    FRRF_MEMORY_BUDGET_GB=2

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import json,urllib.request as u; \
exit(0 if json.load(u.urlopen('http://127.0.0.1:8000/api/health'))['ok'] else 1)"

# One worker, and it is not a default worth changing. The analysis jobs, the
# training runs, the rate-limit window and the caches in front of the model all
# live in this process's memory; a second worker would see none of them and
# would answer /api/analysis/{id}/events with a 404 half the time.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
