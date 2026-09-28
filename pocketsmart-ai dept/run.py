"""
Convenience entry point so you can just run:  python run.py
from the project root (instead of remembering the uvicorn command).
"""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
