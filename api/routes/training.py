"""The corpus, and the corrections people make to what the fly says.

A correction is the most valuable label this project can get: an example the
fly met in the wild, got wrong, and a human marked the exact seconds of. The
endpoint exists so that finding one is not the end of the story.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.ratelimit import limit
from api.services import corpus, corrections

router = APIRouter(tags=["training"])


@router.get("/api/corpus")
def read_corpus() -> dict:
    """What the fly was trained on, and what it made of each track."""
    return corpus.summary()


@router.get("/api/corrections")
def list_corrections() -> dict:
    rows = corrections.load()
    return {"count": len(rows), "corrections": rows}


@router.post("/api/corrections", status_code=201, dependencies=[Depends(limit)])
def add_correction(payload: dict) -> dict:
    try:
        correction = corrections.validate(payload)
    except corrections.InvalidCorrection as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return corrections.append(correction).to_dict()
