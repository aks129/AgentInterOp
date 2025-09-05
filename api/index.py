import os
os.environ.setdefault("APP_ENV", "vercel")
from app.main import app  # FastAPI instance defined in app/main.py