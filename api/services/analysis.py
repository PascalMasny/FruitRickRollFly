"""Running one video past the fly, and narrating it while it happens.

The work is a pipeline of four stages and the interface shows all of them,
because two of them take real time and a spinner that says nothing is worse
than a spinner that says what it is waiting for.
"""

from __future__ import annotations

import asyncio
import functools
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

from api.services import fly as fly_service
from api.services import youtube
from brain.audio import decode
from brain.model import Response

CHUNK = 48
"""Percepts per streamed frame. Small enough that the brain visibly fills in,
large enough that a five-minute video does not become a thousand messages."""


class Stage(StrEnum):
    QUEUED = "queued"
    RESOLVING = "resolving"
    FETCHING = "fetching"
    HEARING = "hearing"
    JUDGING = "judging"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    url: str
    stage: Stage = Stage.QUEUED
    video: dict | None = None
    summary: dict | None = None
    error: str | None = None
    events: list[dict] = field(default_factory=list)
    _subscribers: list[asyncio.Queue] = field(default_factory=list)
    _finished: asyncio.Event = field(default_factory=asyncio.Event)

    def emit(self, kind: str, **payload: Any) -> None:
        event = {"kind": kind, **payload}
        self.events.append(event)
        for queue in self._subscribers:
            queue.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        for event in self.events:
            queue.put_nowait(event)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    @property
    def finished(self) -> asyncio.Event:
        return self._finished


_JOBS: dict[str, Job] = {}
_ORDER: list[str] = []
_MAX_JOBS = 64


def get(job_id: str) -> Job | None:
    return _JOBS.get(job_id)


def create(url: str) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], url=url)
    _JOBS[job.id] = job
    _ORDER.append(job.id)
    while len(_ORDER) > _MAX_JOBS:
        _JOBS.pop(_ORDER.pop(0), None)
    return job


def summarise(response: Response, duration: float | None, elapsed: float) -> dict:
    """Condense a whole response into the handful of numbers the app states."""
    above = np.flatnonzero(response.confidence >= 0.5)
    config = fly_service.fly().config
    return {
        "verdict": response.verdict,
        "committedAt": response.committed_at,
        "firstSuspicionAt": float(response.t[above[0]]) if above.size else None,
        "peakConfidence": response.peak_confidence,
        "meanConfidence": float(response.confidence.mean()),
        "peakDopamine": float(response.dopamine.max()),
        "peakAversion": float(response.aversion.max()),
        "fractionAboveHalf": float((response.confidence >= 0.5).mean()),
        "percepts": len(response),
        "audioSeconds": float(response.t[-1]) if len(response) else 0.0,
        "videoSeconds": duration,
        "analysisSeconds": round(elapsed, 2),
        "realtimeFactor": (
            round(float(response.t[-1]) / elapsed, 1) if elapsed > 0 and len(response) else None
        ),
        "commitThreshold": config.da_commit,
    }


def _frames(response: Response) -> list[dict]:
    """Chunk the timeline for streaming."""
    out = []
    for start in range(0, len(response), CHUNK):
        stop = min(start + CHUNK, len(response))
        out.append(
            {
                "from": start,
                "t": [round(float(x), 4) for x in response.t[start:stop]],
                "confidence": [round(float(x), 4) for x in response.confidence[start:stop]],
                "valence": [round(float(x), 4) for x in response.valence[start:stop]],
                "dopamine": [round(float(x), 4) for x in response.dopamine[start:stop]],
                "aversion": [round(float(x), 4) for x in response.aversion[start:stop]],
                "approach": [round(float(x), 4) for x in response.approach[start:stop]],
                "avoidance": [round(float(x), 4) for x in response.avoidance[start:stop]],
                "kenyon": [sorted(int(i) for i in row) for row in response.kenyon[start:stop]],
                "ear": [[round(float(x), 3) for x in row] for row in response.ear[start:stop]],
            }
        )
    return out


def _work(job: Job, loop: asyncio.AbstractEventLoop) -> None:
    """The blocking half, run in a worker thread."""

    def emit(kind: str, **payload: Any) -> None:
        # call_soon_threadsafe takes positional arguments only, so the
        # keywords are bound here rather than handed to the loop.
        loop.call_soon_threadsafe(functools.partial(job.emit, kind, **payload))

    def stage(value: Stage) -> None:
        job.stage = value
        emit("stage", stage=value.value)

    started = time.perf_counter()
    try:
        stage(Stage.RESOLVING)
        identifier = youtube.video_id(job.url)
        video = youtube.describe(identifier, fly_service.CACHE_DIR)
        job.video = video.to_dict()
        emit("video", video=job.video)

        stage(Stage.FETCHING)
        path = youtube.fetch_audio(identifier, fly_service.CACHE_DIR)

        stage(Stage.HEARING)
        brain = fly_service.fly()
        samples = decode(path, brain.config.sample_rate)
        receptors, t = brain.ear.percepts(samples)
        emit("heard", percepts=int(len(receptors)), seconds=round(float(t[-1]), 2))

        stage(Stage.JUDGING)
        response = brain.respond(receptors, t)
        for frame in _frames(response):
            emit("timeline", **frame)

        job.summary = summarise(response, video.duration, time.perf_counter() - started)
        emit("summary", summary=job.summary)
        stage(Stage.DONE)
    except youtube.NotYouTube as error:
        job.error = str(error)
        job.stage = Stage.FAILED
        emit("error", message=job.error, kind_detail="not-youtube")
        emit("stage", stage=Stage.FAILED.value)
    except Exception as error:
        job.error = f"{type(error).__name__}: {error}"
        job.stage = Stage.FAILED
        emit("error", message=job.error)
        emit("stage", stage=Stage.FAILED.value)
    finally:
        loop.call_soon_threadsafe(job.finished.set)


async def run(job: Job) -> None:
    """Start the pipeline. Returns as soon as the worker thread is scheduled."""
    loop = asyncio.get_running_loop()
    await asyncio.to_thread(_work, job, loop)
