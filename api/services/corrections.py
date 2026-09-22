"""Where the user's corrections go, and the notes page they can write on.

The fly is trained once and then asked about videos it has never met. When it
is wrong about one, that is the most valuable labelled data the project can
get -- it is an out-of-distribution example, found by a human, with the exact
seconds marked. Losing it because there was nowhere to put it would be
careless, so there is somewhere to put it.

Corrections are appended to a JSONL file and never rewritten in place: an
append-only log is the right shape for training data, because the history of
what was said about a video is itself worth keeping, and a later correction
should not silently erase an earlier one.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from api.services import youtube

ROOT = Path(__file__).resolve().parents[2]
CORRECTIONS_PATH = ROOT / "data" / "corrections.jsonl"
NOTES_PATH = ROOT / "data" / "notes.md"

_LOCK = threading.Lock()
"""Appends come from request handlers, which can overlap. One process, one
lock; if this ever grows a second process the file needs O_APPEND semantics
rather than this."""

LABELS = {"rickroll", "not-rickroll"}


@dataclass(frozen=True)
class Correction:
    """One span of one video, labelled by hand."""

    video_id: str
    label: str
    start: float
    end: float
    title: str = ""
    url: str = ""
    note: str = ""
    verdict_was: bool | None = None
    committed_at: float | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)


class InvalidCorrection(ValueError):
    """The span or the label does not make sense."""


def validate(payload: dict) -> Correction:
    label = str(payload.get("label", "")).strip()
    if label not in LABELS:
        raise InvalidCorrection(f"label must be one of {sorted(LABELS)}")

    video_id = str(payload.get("videoId") or payload.get("video_id") or "").strip()
    if not video_id:
        raise InvalidCorrection("which video?")
    # Held to the same shape as a pasted link's id. This endpoint is open, and
    # what it stores is read back by frrf-corrections, where it becomes a glob
    # pattern and the tail of a fetch URL. Nothing downstream reaches a shell,
    # but neither of those has any business taking an arbitrary string.
    if not youtube.VIDEO_ID.match(video_id):
        raise InvalidCorrection("that is not a YouTube video id")

    try:
        start = float(payload.get("start", 0.0))
        end = float(payload.get("end", 0.0))
    except (TypeError, ValueError) as error:
        raise InvalidCorrection("start and end must be seconds") from error
    if not (0.0 <= start < end):
        raise InvalidCorrection("the span must start at or after zero and end after it starts")
    if end - start > 3600:
        raise InvalidCorrection("that span is longer than an hour")

    return Correction(
        video_id=video_id,
        label=label,
        start=round(start, 3),
        end=round(end, 3),
        title=str(payload.get("title") or "")[:300],
        url=str(payload.get("url") or "")[:500],
        note=str(payload.get("note") or "")[:1000],
        verdict_was=payload.get("verdictWas"),
        committed_at=payload.get("committedAt"),
    )


def append(correction: Correction, path: Path | None = None) -> Correction:
    # Resolved here rather than bound as a default argument, because a default
    # is evaluated once at import and is therefore not overridable at all --
    # which makes the path untestable and unconfigurable in the same stroke.
    path = path or CORRECTIONS_PATH
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(correction.to_dict(), ensure_ascii=False) + "\n")
    return correction


def load(path: Path | None = None) -> list[dict]:
    """Every correction ever made, oldest first. A bad line is skipped rather
    than fatal: one malformed row should not cost the whole log."""
    path = path or CORRECTIONS_PATH
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


DEFAULT_NOTES = """# Research notes

Anything written here is saved to `data/notes.md`, so it survives a restart
and can be committed alongside the code it is about.
"""


def read_notes(path: Path | None = None) -> str:
    path = path or NOTES_PATH
    if not path.exists():
        return DEFAULT_NOTES
    return path.read_text(encoding="utf-8")


def write_notes(text: str, path: Path | None = None) -> str:
    path = path or NOTES_PATH
    if len(text) > 400_000:
        raise InvalidCorrection("that is a great deal of prose")
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return text
