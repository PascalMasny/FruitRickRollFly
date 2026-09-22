"""Liveness, and whether there is a trained fly to talk to."""

from __future__ import annotations

from fastapi import APIRouter

from api import settings
from api.services import fly as fly_service

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    """Liveness, and what this particular server is.

    ``admin`` is here so the interface can stop drawing tabs whose endpoints
    are not registered. A public deployment has no workshop and no notes page,
    and a tab that 404s is worse than no tab.
    """
    body = {"ok": True, "admin": settings.admin()}
    try:
        brain = fly_service.fly()
    except fly_service.UntrainedFly as error:
        return body | {"ok": False, "fly": None, "detail": str(error)}
    return body | {
        "fly": {
            "trained": brain.metadata.get("trained"),
            "target": brain.metadata.get("target"),
            "sense": brain.metadata.get("sense", "ear"),
        },
    }
