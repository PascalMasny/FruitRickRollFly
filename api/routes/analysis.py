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
from fastapi.responses import StreamingResponse

from api.schemas import AnalysisAccepted, AnalysisRequest
from api.services import analysis
from api.services import fly as fly_service
from api.services.youtube import NotYouTube, video_id

router = APIRouter(tags=["analysis"])

HEARTBEAT_SECONDS = 15.0
"""Proxies and browsers drop an idle stream; a comment line keeps it open
while a long video downloads."""


@router.post("/api/analysis", response_model=AnalysisAccepted, status_code=202)
async def submit(request: AnalysisRequest, background: BackgroundTasks) -> AnalysisAccepted:
    """Validate the link and start the pipeline.

    The link is checked here as well as in the worker, so a bad paste comes
    back as a 400 with a readable reason instead of as a failed job the client
    has to subscribe to in order to discover.
    """
    try:
        fly_service.fly()
    except fly_service.UntrainedFly as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

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
                if event["kind"] == "stage" and event["stage"] in {"done", "failed"}:
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
