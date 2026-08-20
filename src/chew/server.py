"""Minimal FastAPI health/readiness server for chew (§7-5).

Import is guarded: FastAPI is an optional dep (extras group 'server').
Use `pip install 'youtube-summarizer-kit[server]'` or
`uv pip install -e '.[server]'` to enable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chew.storage.database import Database


def create_app(database: Database | None = None) -> object:
    """Create and return a FastAPI application.

    Raises ImportError with an actionable message when fastapi is not installed.
    """
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
    except ImportError as exc:
        raise ImportError(
            "FastAPI is required to run the health server. "
            "Install it with: pip install 'youtube-summarizer-kit[server]'"
        ) from exc

    app = FastAPI(title="chew health server", docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/readiness")
    async def readiness() -> JSONResponse:
        if database is None:
            return JSONResponse(
                {"status": "ready", "checks": {"database": "not configured"}}
            )
        try:
            database.active_job_count("__probe__")
            checks: dict[str, str] = {"database": "ok"}
            status_code = 200
            status = "ready"
        except Exception as exc:
            checks = {"database": f"error: {exc}"}
            status_code = 503
            status = "degraded"
        return JSONResponse({"status": status, "checks": checks}, status_code=status_code)

    return app
