import os
os.environ.setdefault("APP_ENV", "vercel")
from app.main import app  # FastAPI app instance