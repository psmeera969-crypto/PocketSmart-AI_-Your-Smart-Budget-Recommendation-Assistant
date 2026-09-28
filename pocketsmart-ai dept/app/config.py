"""
Central configuration for PocketSmart AI.
All values are loaded from environment variables (.env file) so
nothing sensitive is hard-coded into the source tree.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env file that sits next to this project's root folder.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # --- Gemini / GenAI ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

    # --- Auth / JWT ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-dev-secret-change-me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

    # --- App ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # --- Paths ---
    APP_DIR: Path = Path(__file__).resolve().parent
    DATA_DIR: Path = APP_DIR / "data"
    USERS_FILE: Path = DATA_DIR / "users.json"
    HISTORY_FILE: Path = DATA_DIR / "history.json"
    TEMPLATES_DIR: Path = APP_DIR / "templates"
    STATIC_DIR: Path = APP_DIR / "static"

    @property
    def is_mock_mode(self) -> bool:
        """True when no Gemini API key is configured - the app then
        falls back to deterministic, rule-based recommendations so it
        still runs end-to-end without any external API calls."""
        return not bool(self.GEMINI_API_KEY)


settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
