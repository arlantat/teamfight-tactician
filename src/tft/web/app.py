"""FastAPI application serving the local TFT companion and its catalog API."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import RequestResponseEndpoint

from tft.config import DB_PATH, WEB_STATIC_PATH
from tft.exceptions import ExplorerQueryError, NewsSourceError
from tft.explorer import ExplorerQuery, ExplorerResult, explore, parse_filters
from tft.news import load_news
from tft.web.catalog import Catalog, CatalogUnavailableError, read_catalog

log = logging.getLogger(__name__)


def create_app(db_path: Path | None = None) -> FastAPI:
    """Create an application with an explicit database for deployment or tests.

    Args:
        db_path: Optional override for the configured catalog database.

    Returns:
        A FastAPI app serving the catalog and browser interface.
    """
    database = db_path if db_path is not None else DB_PATH
    application = FastAPI(title="Teamfight Tactician", version="0.2.0")

    @application.middleware("http")
    async def add_response_headers(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Keep data fresh and revalidate application code after local updates."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        elif request.url.path.startswith("/static/") and request.url.path.endswith(
            (".js", ".css", ".html")
        ):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @application.get("/api/health")
    def health() -> dict[str, str]:
        """Report server availability without requiring a populated database."""
        return {"status": "ok"}

    @application.get("/api/catalog")
    def catalog() -> Catalog:
        """Expose the downloaded static set catalog to the browser."""
        try:
            return read_catalog(database)
        except CatalogUnavailableError as exc:
            log.warning("Catalog unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"{exc} Run scripts/update_static_data.py, then reload.",
            ) from exc

    @application.get("/api/analysis")
    def analysis(game_version: str | None = None) -> dict[str, Any]:
        """Compute comparisons from stored matches without contacting Riot."""
        from tft.analysis.delta_engine import analyze

        try:
            result = analyze(database, game_version=game_version)
        except (FileNotFoundError, sqlite3.Error, ValueError, KeyError) as exc:
            log.warning("Stored match analysis unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Refresh the catalog and harvest compatible match data.",
            ) from exc
        return {
            "versions": result.versions,
            "sample_count": result.sample_count,
            "population": json.loads(result.population.to_json(orient="records")),
            "behavioral": json.loads(result.behavioral.to_json(orient="records")),
            "highrolls": json.loads(result.highrolls.to_json(orient="records")),
        }

    @application.get("/api/explorer")
    def explorer(
        filters: str | None = None,
        game_version: str | None = None,
        rank: str | None = None,
        focus: str | None = None,
    ) -> ExplorerResult:
        """Filter stored ranked boards and return placement statistics."""
        try:
            query = ExplorerQuery(
                filters=parse_filters(filters),
                game_version=game_version or None,
                rank=rank or None,
                focus_unit=focus.strip().lower() if focus and focus.strip() else None,
            )
        except ExplorerQueryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            return explore(database, query)
        except (FileNotFoundError, sqlite3.Error, ValueError, KeyError) as exc:
            log.warning("Match explorer unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Refresh the catalog and harvest compatible match data.",
            ) from exc

    @application.get("/api/news")
    def news() -> dict[str, Any]:
        """Return official TFT patch notes and game updates from Riot's public site."""
        try:
            return load_news(database)
        except NewsSourceError as exc:
            log.warning("Official TFT news unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Official TFT patch notes are unavailable right now.",
            ) from exc

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        """Serve the application shell."""
        return FileResponse(WEB_STATIC_PATH / "index.html", headers={"Cache-Control": "no-cache"})

    application.mount(
        "/static", StaticFiles(directory=WEB_STATIC_PATH, check_dir=False), name="static"
    )
    return application


app = create_app()
