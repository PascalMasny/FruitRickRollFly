"""The application.

One FastAPI app, one process. It serves the JSON API and, if the frontend has
been built, the built frontend as well, so that a single ``uvicorn
api.main:app`` is the whole of the deployment.

One process is load-bearing rather than incidental. The analysis jobs, the
training runs, the rate-limit window and the caches in front of the model all
live in this process's memory, and a second replica would not see any of them.
Scaling out means moving that state somewhere shared first; until then, run
one worker.

What the app *is* depends on where it is running. The workshop starts
processes on the host and the notes page writes files to it, which is the
point on a laptop and is remote code execution on a public address, so those
routes are registered only when :func:`api.settings.admin` says so. They are
left out rather than refused: there is no 403 to find.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from api import settings
from api.routes import analysis, brain, health, notes, training, workshop

ROOT = Path(__file__).resolve().parents[1]
WEB_DIST = ROOT / "web" / "dist"


def create_app() -> FastAPI:
    developing = settings.dev()
    app = FastAPI(
        title="FruitRickRollFly",
        version="0.1.0",
        summary="A fruit fly brain that has learned exactly one song.",
        description=(
            "Give it a YouTube link. It decodes the audio, runs it through a model "
            "of the Drosophila mushroom body, and reports what the fly's dopamine "
            "did about it."
        ),
        # The schema is a map of the admin surface, so it is drawn only where
        # that surface exists.
        docs_url="/docs" if developing else None,
        redoc_url="/redoc" if developing else None,
        openapi_url="/openapi.json" if developing else None,
    )

    hosts = settings.trusted_hosts()
    if hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    origins = settings.cors_origins()
    if origins:
        # Empty in production: the built frontend is served from this same
        # process on this same origin, and CORS never comes up. The list is
        # for Vite's dev server and for anyone who splits the two.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(brain.router)
    app.include_router(analysis.router)
    app.include_router(training.router)
    if settings.admin():
        app.include_router(notes.router)
        app.include_router(workshop.router)

    if WEB_DIST.is_dir():
        # The whole build directory, not just /assets: the frontend also ships
        # the favicon, the icon sheet, and the hemibrain meshes the 3D view
        # loads at runtime, all of which sit at the root of the build. This
        # mount is registered last, so every API route above still wins.
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")

    return app


app = create_app()
