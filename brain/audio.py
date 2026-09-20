"""Johnston's organ: where sound becomes receptor activity.

A fly hears with its antennae. The arista is deflected by the near field of a
sound, the second antennal segment twists, and about 480 mechanosensory
neurons in Johnston's organ report that twist, each tuned to its own band. It
is how a male's courtship song reaches a female, and it is the only hearing
the animal has.

This module is the software equivalent: decode, level, and split sound into
tonotopic channels plus a set of pitch-class channels, then slice the result
into the short percepts the mushroom body will judge. No learning happens
here; the ear has no opinion about Rick Astley.

Everything is NumPy. There is no librosa, no torch, and no model format that
needs a runtime, because a circuit this small should not drag a stack behind
it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from brain.config import BrainConfig

_BLOCK_FRAMES = 4096
"""Spectral frames per processing block, so a long track never materialises a
frame matrix larger than a few hundred megabytes."""


class AudioDecodeError(RuntimeError):
    """ffmpeg could not turn the file into samples."""


def decode(path: str | Path, sample_rate: int = 22_050) -> np.ndarray:
    """Decode any container ffmpeg understands into mono float32 samples."""
    command = [
        "ffmpeg", "-v", "error", "-nostdin",
        "-i", str(path),
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ac", "1", "-ar", str(sample_rate), "-",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise AudioDecodeError(detail[-1] if detail else f"ffmpeg exited {result.returncode}")
    samples = np.frombuffer(result.stdout, dtype="<f4").astype(np.float32, copy=True)
    if samples.size == 0:
        raise AudioDecodeError(f"{path} decoded to zero samples")
    return samples


def level(samples: np.ndarray, target_rms: float) -> np.ndarray:
    """Bring a track to a fixed RMS.

    The gain control downstream is divisive, so it discards absolute loudness
    on its own; what it cannot do is tell a quiet passage from silence without
    a reference. Levelling the track gives it one.
    """
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    if rms < 1e-9:
        return samples
    return (samples * (target_rms / rms)).astype(np.float32)


def _hann(n: int) -> np.ndarray:
    """Periodic Hann window, the one that belongs in an STFT."""
    return (0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / n)).astype(np.float32)


def _hz_to_mel(hz: np.ndarray | float) -> np.ndarray | float:
    return 2595.0 * np.log10(1.0 + np.asarray(hz, dtype=np.float64) / 700.0)


def _mel_to_hz(mel: np.ndarray | float) -> np.ndarray | float:
    return 700.0 * (10.0 ** (np.asarray(mel, dtype=np.float64) / 2595.0) - 1.0)


def mel_filterbank(config: BrainConfig) -> np.ndarray:
    """Triangular, area-normalised mel bank of shape (n_mel, n_bins)."""
    n_bins = config.n_fft // 2 + 1
    bin_hz = np.fft.rfftfreq(config.n_fft, 1.0 / config.sample_rate)
    edges = _mel_to_hz(
        np.linspace(_hz_to_mel(config.mel_fmin), _hz_to_mel(config.mel_fmax), config.n_mel + 2)
    )
    bank = np.zeros((config.n_mel, n_bins), dtype=np.float32)
    for m in range(config.n_mel):
        low, centre, high = edges[m], edges[m + 1], edges[m + 2]
        rising = (bin_hz - low) / max(centre - low, 1e-9)
        falling = (high - bin_hz) / max(high - centre, 1e-9)
        bank[m] = np.clip(np.minimum(rising, falling), 0.0, None)
        total = bank[m].sum()
        if total > 0:
            bank[m] /= total
    return bank


def chroma_filterbank(config: BrainConfig) -> np.ndarray:
    """Pitch-class bank of shape (n_chroma, chroma_bins).

    Each bin votes for the pitch class of its nearest semitone, and only if it
    lies within ``chroma_tolerance_cents`` of that semitone's centre. Bins
    sitting between two semitones are dropped rather than assigned to
    whichever is marginally closer.
    """
    n_bins = config.chroma_n_fft // 2 + 1
    bin_hz = np.fft.rfftfreq(config.chroma_n_fft, 1.0 / config.sample_rate)
    bank = np.zeros((config.n_chroma, n_bins), dtype=np.float32)
    midi = 69.0 + 12.0 * np.log2(np.maximum(bin_hz, 1e-9) / 440.0)
    off_centre = np.abs(midi - np.rint(midi)) * 100.0
    usable = (
        (bin_hz >= config.chroma_fmin)
        & (bin_hz <= config.chroma_fmax)
        & (off_centre < config.chroma_tolerance_cents)
    )
    pitch_class = np.rint(midi).astype(int) % config.n_chroma
    for b in np.flatnonzero(usable):
        bank[pitch_class[b], b] = 1.0
    counts = bank.sum(axis=1, keepdims=True)
    return bank / np.maximum(counts, 1.0)


class JohnstonsOrgan:
    """The ear. Turns samples into a stream of receptor percepts."""

    def __init__(self, config: BrainConfig | None = None) -> None:
        self.config = config or BrainConfig()
        self._window = _hann(self.config.n_fft)
        self._chroma_window = _hann(self.config.chroma_n_fft)
        self._mel = mel_filterbank(self.config)
        self._chroma = chroma_filterbank(self.config)

    # ── spectral stage ───────────────────────────────────────────────────────

    def channel_frames(self, samples: np.ndarray) -> np.ndarray:
        """Per-frame channel amplitudes, shape (n_frames, n_mel + n_chroma).

        Two transforms, sharing a frame grid. Timbre is read off a short
        window because that is where transients live; pitch is read off a long
        one because frequency resolution is what pitch needs. The long window
        is centred on the short one, so both describe the same instant.
        """
        config = self.config
        n_fft, hop = config.n_fft, config.frame_hop
        if samples.size < n_fft:
            samples = np.pad(samples, (0, n_fft - samples.size))
        n_frames = 1 + (samples.size - n_fft) // hop
        channels = np.empty((n_frames, config.channels_per_subframe), dtype=np.float32)

        for start in range(0, n_frames, _BLOCK_FRAMES):
            stop = min(start + _BLOCK_FRAMES, n_frames)
            offsets = (np.arange(start, stop) * hop)[:, None] + np.arange(n_fft)[None, :]
            frames = samples[offsets] * self._window
            magnitude = np.abs(np.fft.rfft(frames, axis=1)).astype(np.float32)
            channels[start:stop, : config.n_mel] = magnitude @ self._mel.T

        channels[:, config.n_mel :] = self._chroma_frames(samples, n_frames)
        return channels

    def _chroma_frames(self, samples: np.ndarray, n_frames: int) -> np.ndarray:
        """The long-window half of :meth:`channel_frames`."""
        config = self.config
        width = config.chroma_n_fft
        lead = (width - config.n_fft) // 2
        padded = np.pad(samples, (lead, width))
        block = max(1, _BLOCK_FRAMES // (width // config.n_fft))

        out = np.empty((n_frames, config.n_chroma), dtype=np.float32)
        for start in range(0, n_frames, block):
            stop = min(start + block, n_frames)
            rows = (np.arange(start, stop) * config.frame_hop)[:, None]
            offsets = rows + np.arange(width)[None, :]
            frames = padded[offsets] * self._chroma_window
            magnitude = np.abs(np.fft.rfft(frames, axis=1)).astype(np.float32)
            out[start:stop] = magnitude @ self._chroma.T
        return out

    # ── percept stage ────────────────────────────────────────────────────────

    def percepts(
        self, samples: np.ndarray, hop_frames: int | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Slice a track into percepts.

        Returns ``(receptors, t_end)``. ``receptors`` has shape
        ``(n_percepts, n_receptors)``; ``t_end`` holds, for each percept, the
        moment its last sample was heard. Reaction time is measured against
        ``t_end``, because that is the earliest the fly could have known.
        """
        config = self.config
        hop = hop_frames if hop_frames is not None else config.window_hop_frames
        channels = self.channel_frames(level(samples, config.target_rms))

        width = config.window_frames
        if channels.shape[0] < width:
            channels = np.pad(channels, ((0, width - channels.shape[0]), (0, 0)))
        starts = np.arange(0, channels.shape[0] - width + 1, hop)
        if starts.size == 0:
            starts = np.zeros(1, dtype=int)

        # Sub-frame means via a cumulative sum: one pass regardless of overlap.
        cumulative = np.concatenate(
            [
                np.zeros((1, channels.shape[1]), dtype=np.float64),
                np.cumsum(channels, axis=0, dtype=np.float64),
            ]
        )
        sub = config.subframe_frames
        parts = []
        for s in range(config.subframes):
            lo = starts + s * sub
            parts.append(((cumulative[lo + sub] - cumulative[lo]) / sub).astype(np.float32))
        receptors = np.concatenate(parts, axis=1)

        t_end = ((starts + width - 1) * config.frame_hop + config.n_fft) / config.sample_rate
        return receptors, t_end.astype(np.float32)

    def percepts_from_file(
        self, path: str | Path, hop_frames: int | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        samples = decode(path, self.config.sample_rate)
        return self.percepts(samples, hop_frames=hop_frames)
