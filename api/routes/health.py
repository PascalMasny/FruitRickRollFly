"""Liveness, and whether there is a trained fly to talk to."""

from __future__ import annotations

from fastapi import APIRouter

from api.services import fly as fly_service

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    try:
        brain = fly_service.fly()
    except fly_service.UntrainedFly as error:
        return {"ok": False, "fly": None, "detail": str(error)}
    return {
        "ok": True,
        "fly": {
            "trained": brain.metadata.get("trained"),
            "target": brain.metadata.get("target"),
        },
    }
