"""The notes page.

Admin-only, and registered by :func:`api.main.create_app` only when
:func:`api.settings.admin` is on. A ``PUT`` here overwrites a file on the host
with whatever was sent, which is exactly what is wanted from the machine the
research is happening on and is an open file write from anywhere else.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.services import corrections

router = APIRouter(tags=["notes"])


@router.get("/api/notes")
def read_notes() -> dict:
    return {"text": corrections.read_notes()}


@router.put("/api/notes")
def save_notes(payload: dict) -> dict:
    try:
        text = corrections.write_notes(str(payload.get("text", "")))
    except corrections.InvalidCorrection as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"text": text, "saved": True}
