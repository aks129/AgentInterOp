import os
os.environ.setdefault("APP_ENV", "vercel")
from app.main import app  # your FastAPI instance: app = FastAPI() in app/main.py