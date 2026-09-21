"""Running the training commands from the browser, safely.

Training from a web page is a shell-injection question before it is anything
else, so there is no shell and no user-supplied command. A job is one of a
fixed set of names; its argv is built here from a template; and the only
things the caller can influence are a handful of scalars that are range
checked, plus a model name matched against a strict pattern. Nothing the
client sends is ever concatenated into a command.

One job at a time. These are CPU-bound for minutes and two at once would
simply take twice as long while making the log unreadable.
"""

from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,48}$")
"""A model filename the caller may choose. No separators, so it cannot leave
models/, and no leading dot, so it cannot be hidden."""

MAX_LINES = 4000
"""Kept per run. A full cross-validation prints a few hundred lines; this is
generous and still bounded."""


@dataclass
class Job:
    """One template. `build` turns validated options into argv."""

    name: str
    label: str
    describe: str
    build: object


def _train(options: dict, *, sense: str) -> list[str]:
    epochs = int(options.get("epochs", 60))
    seed = int(options.get("seed", 7))
    floor = float(options.get("minSpecificity", 0.95))
    if not 1 <= epochs <= 500:
        raise ValueError("epochs must be between 1 and 500")
    if not 0 <= seed <= 2**31:
        raise ValueError("seed out of range")
    if not 0.0 <= floor <= 1.0:
        raise ValueError("the specificity floor must be a fraction")

    name = str(options.get("name") or ("fly_eye" if sense == "eye" else "fly_brain"))
    if not SAFE_NAME.match(name):
        raise ValueError("a model name is letters, digits, dot, dash and underscore")
    stem = name.removesuffix(".npz")

    argv = [
        sys.executable, "-m", "training.train",
        "--sense", sense,
        "--epochs", str(epochs),
        "--seed", str(seed),
        "--min-specificity", str(floor),
        "--out", f"models/{stem}.npz",
        "--metrics", f"models/metrics-{stem}.json",
        "--traces", f"models/traces-{stem}.npz",
    ]
    if sense == "eye":
        argv += ["--features", "data/features-eye", "--min-activity", "0.004"]
    if options.get("withCorrections"):
        merged = ROOT / "data" / "manifest-with-corrections.json"
        if not merged.exists():
            raise ValueError("no merged manifest yet; run 'fold corrections' first")
        argv += ["--manifest", "data/manifest-with-corrections.json"]
    return argv


JOBS: dict[str, Job] = {
    "train-ear": Job(
        "train-ear", "train on sound",
        "Cross-validate and ship a fly that listens.",
        lambda options: _train(options, sense="ear"),
    ),
    "train-eye": Job(
        "train-eye", "train on sight",
        "The same circuit on the visual percepts. It has never reached the "
        "specificity floor; see finding 7.",
        lambda options: _train(options, sense="eye"),
    ),
    "fetch": Job(
        "fetch", "fetch the corpus",
        "Download the audio corpus and turn it into percepts.",
        lambda options: [sys.executable, "-m", "training.fetch"],
    ),
    "watch": Job(
        "watch", "fetch the video corpus",
        "Download the corpus as video and run it through the eye.",
        lambda options: [sys.executable, "-m", "training.watch"],
    ),
    "corrections": Job(
        "corrections", "fold corrections",
        "Turn hand-marked spans into percepts and write a merged manifest.",
        lambda options: [sys.executable, "-m", "training.corrections"],
    ),
    "evaluate": Job(
        "evaluate", "redraw the figures",
        "Redraw docs/img from the current traces.",
        lambda options: [sys.executable, "-m", "training.evaluate"],
    ),
    "insights": Job(
        "insights", "rewrite the insights",
        "Redraw the corpus figures and rewrite docs/TRAINING.md.",
        lambda options: [sys.executable, "-m", "training.insights"],
    ),
}


@dataclass
class Run:
    id: str
    job: str
    argv: list[str]
    started: float = field(default_factory=time.time)
    finished: float | None = None
    status: str = "running"
    code: int | None = None
    lines: deque = field(default_factory=lambda: deque(maxlen=MAX_LINES))
    process: subprocess.Popen | None = None

    def to_dict(self, tail: int = 0) -> dict:
        body = {
            "id": self.id,
            "job": self.job,
            "label": JOBS[self.job].label if self.job in JOBS else self.job,
            "command": " ".join(self.argv[1:]),
            "status": self.status,
            "code": self.code,
            "started": self.started,
            "seconds": round((self.finished or time.time()) - self.started, 1),
            "lines": len(self.lines),
        }
        if tail:
            body["tail"] = list(self.lines)[-tail:]
        return body


_RUNS: dict[str, Run] = {}
_ORDER: list[str] = []
_LOCK = threading.Lock()


class Busy(RuntimeError):
    """Something is already running."""


def current() -> Run | None:
    for identifier in reversed(_ORDER):
        run = _RUNS[identifier]
        if run.status == "running":
            return run
    return None


def history(limit: int = 12) -> list[dict]:
    return [_RUNS[i].to_dict() for i in reversed(_ORDER[-limit:])]


def get(identifier: str) -> Run | None:
    return _RUNS.get(identifier)


def start(job_name: str, options: dict | None = None) -> Run:
    if job_name not in JOBS:
        raise KeyError(job_name)
    with _LOCK:
        if current() is not None:
            raise Busy("a job is already running")
        argv = JOBS[job_name].build(options or {})
        run = Run(id=uuid.uuid4().hex[:12], job=job_name, argv=argv)
        _RUNS[run.id] = run
        _ORDER.append(run.id)

    def pump() -> None:
        try:
            # No shell, cwd pinned to the repository, stderr folded into
            # stdout so the log reads in the order it happened.
            process = subprocess.Popen(  # noqa: S603 - argv is built from a template
                argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            run.process = process
            assert process.stdout is not None
            for line in process.stdout:
                run.lines.append(line.rstrip("\n"))
            run.code = process.wait()
            run.status = "done" if run.code == 0 else "failed"
        except Exception as error:
            run.lines.append(f"{type(error).__name__}: {error}")
            run.status = "failed"
            run.code = -1
        finally:
            run.finished = time.time()

    threading.Thread(target=pump, name=f"job-{run.id}", daemon=True).start()
    return run


def stop(identifier: str) -> Run | None:
    run = _RUNS.get(identifier)
    if run is None or run.process is None or run.status != "running":
        return run
    run.process.terminate()
    run.status = "stopped"
    run.lines.append("-- stopped --")
    return run


def catalogue() -> list[dict]:
    return [
        {"name": job.name, "label": job.label, "describe": job.describe}
        for job in JOBS.values()
    ]
