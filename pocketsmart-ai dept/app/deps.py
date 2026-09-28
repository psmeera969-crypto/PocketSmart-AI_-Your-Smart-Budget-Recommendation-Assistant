"""Shared, app-wide dependencies (kept in one place to avoid duplicate
Jinja2Templates instances across route modules)."""
from fastapi.templating import Jinja2Templates
from app.config import settings

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))
