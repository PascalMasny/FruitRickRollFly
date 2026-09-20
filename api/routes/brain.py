"""What the fly is: circuit sizes, corpus, and its out-of-fold scores.

The interface draws the mushroom body from this, so the numbers here are the
model's, never hard-coded in the frontend. Change the Kenyon cell count and
the picture changes with it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.services import fly as fly_service

router = APIRouter(tags=["brain"])


@router.get("/api/brain")
def describe_brain() -> dict:
    try:
        return fly_service.card()
    except fly_service.UntrainedFly as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/api/brain/metrics")
def full_metrics() -> dict:
    """The whole of models/metrics.json, for anyone who wants the folds."""
    report = fly_service.metrics()
    if not report:
        raise HTTPException(status_code=404, detail="no metrics.json; train the fly first")
    return report
