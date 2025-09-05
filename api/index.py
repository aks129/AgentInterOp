# api/index.py
import traceback
import os

# Set a flag so your code can skip stuff that doesn't work in serverless
os.environ.setdefault("APP_ENV", "vercel")

try:
    # IMPORTANT: make sure app/ is a package
    from app.main import app as _fastapi_app
    app = _fastapi_app
except Exception as e:
    # Fall back to a tiny ASGI app that reports the import error in-browser
    from fastapi import FastAPI, Response
    import sys

    tb = "".join(traceback.format_exception(e))
    print("=== VERCEL IMPORT FAILURE ===")
    print(tb, file=sys.stderr, flush=True)

    app = FastAPI()

    @app.get("/{path:path}")
    def failed(path: str):
        # Text response so Vercel doesn't hide it
        return Response(
            content=(
                "Startup import failed in api/index.py\n\n"
                "=== Exception ===\n" + tb +
                "\n\nFix the error in app.main or its imports and redeploy."
            ),
            media_type="text/plain",
            status_code=500,
        )