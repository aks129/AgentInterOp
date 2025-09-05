# Vercel Python Function entrypoint (ASGI)
# Exposes your FastAPI app as `app` for Vercel

from app.main import app  # <-- your existing FastAPI instance
# That's it. Vercel detects `app` and runs it as an ASGI app.