"""The corpus, as the training-data page needs it.

Assembled from what is already on disk -- the manifest, the out-of-fold
verdicts in metrics.json, and the timelines in traces.npz -- so this endpoint
never needs the network and never retrains anything. It is read once and
cached, because none of it changes without a retrain.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "models" / "metrics.json"
TRACES_PATH = ROOT / "models" / "traces.npz"
MANIFEST_PATH = ROOT / "training" / "manifest.json"

POSITIVE_LABEL = "rickroll"


@functools.lru_cache(maxsize=1)
def summary() -> dict:
    """Every track, with what the fly made of it out of fold."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    metrics = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}

    spreads: dict[str, dict] = {}
    if TRACES_PATH.exists():
        from training.traces import load as load_traces

        for family, traces in load_traces(TRACES_PATH).items():
            for trace in traces:
                low, mid, high = np.percentile(trace.confidence, [5, 50, 95])
                spreads.setdefault(trace.id, {})[family] = {
                    "p05": round(float(low), 4),
                    "median": round(float(mid), 4),
                    "p95": round(float(high), 4),
                    "peak": round(float(trace.confidence.max()), 4),
                    "percepts": int(len(trace.confidence)),
                    "seconds": round(float(trace.t[-1]), 1),
                }

    verdicts: dict[str, dict] = {}
    for family, key in (("rendition", "unheard_rendition"), ("upload", "unheard_upload")):
        for verdict in metrics.get(key, {}).get("verdicts", []):
            verdicts.setdefault(verdict["id"], {})[family] = {
                "committed": bool(verdict["committed"]),
                "latency": verdict["latency"],
            }

    tracks = []
    for entry in manifest.get("tracks", []):
        identifier = entry["id"]
        tracks.append({
            "id": identifier,
            "title": entry.get("title", identifier),
            "kind": entry.get("kind", "unknown"),
            "group": entry.get("group", ""),
            "use": entry.get("use", "train"),
            # `target` in the manifest is the song's name, not a label; the
            # per-track label is the thing to compare against.
            "positive": entry.get("label") == POSITIVE_LABEL,
            "watchUrl": f"https://www.youtube.com/watch?v={identifier}",
            "spread": spreads.get(identifier, {}),
            "verdict": verdicts.get(identifier, {}),
        })

    return {
        "target": manifest.get("target"),
        "curationRules": manifest.get("curation_rules"),
        "tracks": tracks,
        "commitment": metrics.get("commitment", {}),
        "performance": {
            "rendition": metrics.get("unheard_rendition", {}).get("tracks", {}),
            "upload": metrics.get("unheard_upload", {}).get("tracks", {}),
        },
    }
