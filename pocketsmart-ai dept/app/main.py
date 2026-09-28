"""
PocketSmart AI - FastAPI application entry point.

Run directly for local development:
    python -m app.main
or from the project root:
    python run.py
or with the reload-enabled dev server:
    uvicorn app.main:app --reload
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.deps import templates
from app.routes import auth_routes, history_routes, pages_routes, planner_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("pocketsmart")

app = FastAPI(
    title="PocketSmart AI",
    description="Your Smart Budget & Recommendation Assistant - "
    "GenAI-powered budgeting for Home Interiors, Parties, and Jewelry.",
    version="1.0.0",
)

# --- CORS: allow the frontend (and local dev tools) to call the API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files (CSS/JS) ---
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# --- Routers ---
app.include_router(pages_routes.router)
app.include_router(auth_routes.router)
app.include_router(planner_routes.router)
app.include_router(history_routes.router)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Redirect unauthenticated page visits to /login instead of showing
    a bare 401 JSON blob; keep JSON errors for API/XHR calls."""
    wants_json = request.url.path.startswith(("/generate-", "/api/", "/session-", "/recommendations-", "/token"))
    if exc.status_code == 401 and not wants_json:
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/login")
    if exc.status_code == 404 and not wants_json:
        return templates.TemplateResponse(
            request, "404.html", {}, status_code=404
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.on_event("startup")
async def on_startup():
    """Initializes essential application services and loads configuration
    settings when the FastAPI server starts."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    mode = "MOCK (rule-based fallback)" if settings.is_mock_mode else f"LIVE (Gemini: {settings.GEMINI_MODEL})"
    logger.info("PocketSmart AI starting up | recommendation engine mode: %s", mode)
    logger.info("Data directory ready at: %s", settings.DATA_DIR)


@app.get("/health", tags=["meta"])
async def health_check():
    return {
        "status": "ok",
        "app_env": settings.APP_ENV,
        "mock_mode": settings.is_mock_mode,
        "gemini_model": settings.GEMINI_MODEL,
    }


# Entry point of the FastAPI application that starts the server using
# uvicorn when the script is run directly.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
