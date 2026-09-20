"""Submit a link, then watch the fly hear it.

The work runs in a background task and the client follows a server-sent event
stream. SSE rather than a websocket because the traffic is one-directional and
a reconnecting EventSource is less code on both ends than a socket protocol.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from api.schemas import AnalysisAccepted, AnalysisRequest
from api.services import analysis
from api.services import fly as fly_service
from api.services.youtube import NotYouTube, is_shortener, video_id

router = APIRouter(tags=["analysis"])

HEARTBEAT_SECONDS = 15.0
"""Proxies and browsers drop an idle stream; a comment line keeps it open
while a long video downloads."""


@router.post("/api/analysis", response_model=AnalysisAccepted, status_code=202)
async def submit(request: AnalysisRequest, background: BackgroundTasks) -> AnalysisAccepted:
    """Validate the link and start the pipeline.

    The link is checked here as well as in the worker, so a bad paste comes
    back as a 400 with a readable reason instead of as a failed job the client
    has to subscribe to in order to discover. Shorteners are the exception:
    they are resolved in the worker, because deciding about one means making a
    request.
    """
    try:
        fly_service.fly()
    except fly_service.UntrainedFly as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    # A shortener cannot be checked without following it, and following it
    # needs the network, so it is let through here and resolved in the worker
    # -- where, if it does not land on YouTube, it fails like any other link
    # that is not YouTube. Everything else is still refused before any fetch.
    if not is_shortener(request.url):
        try:
            video_id(request.url)
        except NotYouTube as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    job = analysis.create(request.url)
    background.add_task(analysis.run, job)
    return AnalysisAccepted(
        id=job.id, stage=job.stage.value, events=f"/api/analysis/{job.id}/events"
    )


@router.get("/api/analysis/{job_id}")
def snapshot(job_id: str) -> dict:
    """The job as it stands, for a client that would rather poll."""
    job = analysis.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="no such analysis")
    return {
        "id": job.id,
        "stage": job.stage.value,
        "video": job.video,
        "summary": job.summary,
        "error": job.error,
    }


@router.get("/api/analysis/{job_id}/media")
def media(job_id: str) -> FileResponse:
    """The downloaded video, served from here rather than embedded from YouTube.

    Serving it ourselves is the whole point: the uploaders most likely to be
    worth asking about are the ones who disable embedding, and the embed for
    those is a grey box saying the video is unavailable. FileResponse handles
    Range, so the player can still seek.
    """
    job = analysis.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="no such analysis")
    if job.media is None or not job.media.exists():
        raise HTTPException(status_code=404, detail="nothing downloaded for that analysis")
    return FileResponse(job.media, media_type=_media_type(job.media.suffix))


def _media_type(suffix: str) -> str:
    return {
        ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
        ".mkv": "video/x-matroska", ".mov": "video/quicktime",
    }.get(suffix.lower(), "application/octet-stream")


@router.get("/api/analysis/{job_id}/events")
async def events(job_id: str) -> StreamingResponse:
    job = analysis.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="no such analysis")

    async def stream() -> AsyncIterator[str]:
        queue = job.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    if job.finished.is_set() and queue.empty():
                        break
                    yield ": still here\n\n"
                    continue
                yield f"event: {event['kind']}\ndata: {json.dumps(event)}\n\n"
                # Not `done`: the analysis finishes before the video has
                # finished downloading, and hanging up there loses the event
                # that tells the player where to find it.
                if event["kind"] == "end":
                    break
        finally:
            job.unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
