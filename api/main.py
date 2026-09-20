"""The application.

One FastAPI app, one process, no container. It serves the JSON API and, if the
frontend has been built, the built frontend as well, so that a single
``uvicorn api.main:app`` is the whole of the deployment.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import analysis, brain, health

ROOT = Path(__file__).resolve().parents[1]
WEB_DIST = ROOT / "web" / "dist"

DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
"""Vite's dev server. In production the frontend is served from this same
origin and CORS never comes up."""


def create_app() -> FastAPI:
    app = FastAPI(
        title="FruitRickRollFly",
        version="0.1.0",
        summary="A fruit fly brain that has learned exactly one song.",
        description=(
            "Give it a YouTube link. It decodes the audio, runs it through a model "
            "of the Drosophila mushroom body, and reports what the fly's dopamine "
            "did about it."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(brain.router)
    app.include_router(analysis.router)

    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(WEB_DIST / "index.html")

    return app


app = create_app()
