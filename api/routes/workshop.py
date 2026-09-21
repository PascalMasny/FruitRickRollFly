"""Picking a fly, and running the training commands.

Everything here is a local development surface: it starts processes on the
machine the server runs on. The job names are a fixed set and their arguments
are built from templates in api.services.trainer, so nothing a client sends
reaches a shell.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.services import fly as fly_service
from api.services import models, trainer

router = APIRouter(tags=["workshop"])


@router.get("/api/models")
def list_models() -> dict:
    return models.state()


@router.post("/api/models/active")
def set_active(payload: dict) -> dict:
    sense = str(payload.get("sense", "ear"))
    name = payload.get("name")
    try:
        models.choose(sense, None if name in (None, "", "default") else str(name))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    # The server holds one fly in a cache; swapping the choice has to drop it
    # or the next request answers with the old one.
    fly_service.forget()
    return models.state()


@router.get("/api/jobs")
def list_jobs() -> dict:
    running = trainer.current()
    return {
        "jobs": trainer.catalogue(),
        "running": running.to_dict(tail=40) if running else None,
        "history": trainer.history(),
    }


@router.post("/api/jobs", status_code=202)
def start_job(payload: dict) -> dict:
    name = str(payload.get("job", ""))
    try:
        run = trainer.start(name, payload.get("options") or {})
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"no job called {name}") from error
    except trainer.Busy as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return run.to_dict()


@router.get("/api/jobs/{run_id}")
def read_job(run_id: str, tail: int = 200) -> dict:
    run = trainer.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="no such run")
    return run.to_dict(tail=max(0, min(tail, trainer.MAX_LINES)))


@router.post("/api/jobs/{run_id}/stop")
def stop_job(run_id: str) -> dict:
    run = trainer.stop(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="no such run")
    return run.to_dict()
