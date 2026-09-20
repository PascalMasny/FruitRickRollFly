"""What the fly sees, which is almost nothing, very fast.

A Drosophila eye has about 750 ommatidia. That is roughly a 32x24 picture, and
no amount of wanting will get a face out of it: whatever this pathway learns
about the 1987 video, it does not learn what Rick Astley looks like. What the
fly is extraordinary at is time. Flicker fusion runs near 200 Hz against our
sixty, and the whole visual system behind those ommatidia is built to measure
motion rather than to recognise shapes.

So this is a motion pathway, and it is the textbook one:

    ommatidia ──► Reichardt correlators ──► wide-field tangential cells
    32 x 24       delayed x undelayed       12 fields x 4 directions
    (hexagonal)   between neighbours        + 12 flicker = 60 channels

A Reichardt detector multiplies the delayed signal from one ommatidium by the
undelayed signal from its neighbour, and subtracts the mirror of that product.
It responds to motion in one direction and is inhibited by the other, which is
what the medulla actually does and why a fly is so hard to swat. The lobula
plate then pools thousands of those into a handful of wide-field cells, which
is what is modelled here as twelve fields.

Sixty channels per frame, three sub-frames to a percept, 180 receptors -- the
same shape the ear produces, so the same calyx can read either.

What it cannot do, stated plainly: a still frame carries no motion, so a
Rickroll that is a photograph is invisible to it. That is a property of the
fly, not an oversight.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from brain.config import BrainConfig


class VideoDecodeError(RuntimeError):
    """ffmpeg could not get pictures out of the file."""


def frames(path: str | Path, config: BrainConfig) -> np.ndarray:
    """Decode to a stack of ommatidial images, shape ``(n, rows, columns)``.

    Twice the columns are asked of ffmpeg and averaged down here, because the
    ommatidia are laid out hexagonally: odd rows sit half a facet to the side
    of even ones. `area` scaling rather than the default bicubic, because an
    ommatidium integrates the light falling on it rather than interpolating a
    sample.
    """
    rows, columns = config.eye_rows, config.eye_columns
    wide = columns * 2
    command = [
        "ffmpeg", "-v", "error", "-nostdin", "-i", str(path),
        "-vf", f"fps={config.eye_fps},scale={wide}:{rows}:flags=area",
        "-pix_fmt", "gray", "-f", "rawvideo", "-",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise VideoDecodeError(detail[-1] if detail else f"ffmpeg exited {result.returncode}")

    flat = np.frombuffer(result.stdout, dtype=np.uint8)
    per_frame = rows * wide
    count = flat.size // per_frame
    if count == 0:
        raise VideoDecodeError(f"{path} decoded to zero frames")
    grid = flat[: count * per_frame].reshape(count, rows, wide).astype(np.float32) / 255.0

    # Hexagonal lattice: even rows take facet pairs (0,1), (2,3), ...; odd rows
    # take (1,2), (3,4), ..., which offsets them by half a facet.
    out = np.empty((count, rows, columns), dtype=np.float32)
    even = grid[:, 0::2, :]
    out[:, 0::2, :] = 0.5 * (even[:, :, 0 : wide - 1 : 2] + even[:, :, 1:wide:2])
    odd = grid[:, 1::2, :]
    shifted = np.concatenate([odd[:, :, 1:], odd[:, :, -1:]], axis=2)
    out[:, 1::2, :] = 0.5 * (shifted[:, :, 0 : wide - 1 : 2] + shifted[:, :, 1:wide:2])
    return out


class Eye:
    """Ommatidia, motion detectors, and the wide-field cells that pool them."""

    def __init__(self, config: BrainConfig | None = None) -> None:
        self.config = config or BrainConfig()

    # ── channel stage ────────────────────────────────────────────────────────

    def channel_frames(self, pictures: np.ndarray) -> np.ndarray:
        """One row of channels per video frame, shape ``(n, 60)``."""
        config = self.config
        if len(pictures) < 2:
            pictures = np.repeat(pictures, 2, axis=0)

        # The delay line: a first-order low pass, which is what the correlator
        # in the medulla uses rather than a fixed lag.
        keep = float(np.exp(-1.0 / (config.eye_fps * max(config.eye_tau, 1e-6))))
        delayed = np.empty_like(pictures)
        delayed[0] = pictures[0]
        for i in range(1, len(pictures)):
            delayed[i] = keep * delayed[i - 1] + (1.0 - keep) * pictures[i]

        # Reichardt correlators between neighbouring facets, both axes. The
        # subtraction is the whole trick: it cancels a uniform brightening and
        # leaves a signal whose sign is the direction of travel.
        horizontal = (
            delayed[:, :, :-1] * pictures[:, :, 1:] - delayed[:, :, 1:] * pictures[:, :, :-1]
        )
        vertical = (
            delayed[:, :-1, :] * pictures[:, 1:, :] - delayed[:, 1:, :] * pictures[:, :-1, :]
        )
        flicker = np.abs(np.diff(pictures, axis=0, prepend=pictures[:1]))

        parts = [
            *self._pool_directional(horizontal),
            *self._pool_directional(vertical),
            self._pool(flicker),
        ]
        return np.concatenate(parts, axis=1).astype(np.float32)

    def _pool(self, field: np.ndarray) -> np.ndarray:
        """Average a per-facet field into the wide-field tangential cells."""
        config = self.config
        n, rows, columns = field.shape
        ry, rx = config.eye_fields_y, config.eye_fields_x
        # Trim rather than pad: the edge facets a field cannot cover evenly are
        # the periphery, and the tangential cells do not reach the rim either.
        rows -= rows % ry
        columns -= columns % rx
        block = field[:, :rows, :columns].reshape(n, ry, rows // ry, rx, columns // rx)
        return block.mean(axis=(2, 4)).reshape(n, ry * rx)

    def _pool_directional(self, field: np.ndarray) -> list[np.ndarray]:
        """Half-wave rectify into two direction-selective populations.

        A tangential cell depolarises for motion one way and hyperpolarises for
        the other, and the calyx downstream cannot read a negative rate, so the
        two directions are carried as two non-negative channels.
        """
        pooled = self._pool(field)
        return [np.maximum(pooled, 0.0), np.maximum(-pooled, 0.0)]

    # ── percept stage ────────────────────────────────────────────────────────

    def percepts(
        self, pictures: np.ndarray, hop_seconds: float | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Slice a video into percepts, as :meth:`brain.audio.Ear.percepts` does.

        Returns ``(receptors, t_end)``. The timing convention is the ear's, so
        a visual percept and an auditory one that share an index describe the
        same moment and the same circuit can be fed either.
        """
        config = self.config
        channels = self.channel_frames(pictures)
        # Motion is scale-free in the way loudness is not: a dark video and a
        # bright one differ by a gain the gain control downstream would rather
        # not have to undo.
        # Normalised per video, and gated. Dividing by the video's own peak is
        # right for a video that moves and catastrophic for one that does not:
        # it scales the compression shimmer of a photograph up into something
        # that looks like choreography. Capping the divisor is not enough on
        # its own, because a still image's noise then simply arrives at the cap
        # -- so the whole pathway is also scaled by how confident we are that
        # anything moved at all, which goes to zero for a photograph and to one
        # for a music video.
        floor = config.eye_activity_floor
        peak = float(np.percentile(np.abs(channels), 99.5)) if channels.size else 0.0
        moving = peak / (peak + floor)
        channels = channels * (moving / max(peak, floor))

        width = max(1, int(round(config.window_seconds * config.eye_fps)))
        step = config.window_hop_seconds if hop_seconds is None else hop_seconds
        hop = max(1, int(round(step * config.eye_fps)))
        if channels.shape[0] < width:
            channels = np.pad(channels, ((0, width - channels.shape[0]), (0, 0)))
        starts = np.arange(0, channels.shape[0] - width + 1, hop)
        if starts.size == 0:
            starts = np.zeros(1, dtype=int)

        cumulative = np.concatenate(
            [
                np.zeros((1, channels.shape[1]), dtype=np.float64),
                np.cumsum(channels, axis=0, dtype=np.float64),
            ]
        )
        sub = max(1, width // config.subframes)
        parts = []
        for s in range(config.subframes):
            lo = np.minimum(starts + s * sub, channels.shape[0] - sub)
            parts.append(((cumulative[lo + sub] - cumulative[lo]) / sub).astype(np.float32))
        receptors = np.concatenate(parts, axis=1)

        t_end = (starts + width - 1) / config.eye_fps
        return receptors, t_end.astype(np.float32)

    def percepts_from_file(
        self, path: str | Path, hop_seconds: float | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        return self.percepts(frames(path, self.config), hop_seconds=hop_seconds)
