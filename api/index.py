import os
import sys
import traceback

from fastapi import FastAPI, Response

os.environ.setdefault("APP_ENV", "vercel")


def _build_app() -> FastAPI:
    try:
        from app.main import app as real_app

        return real_app
    except Exception as e:
        tb = "".join(traceback.format_exception(e))
        print("=== VERCEL IMPORT FAILURE ===", file=sys.stderr, flush=True)
        print(tb, file=sys.stderr, flush=True)

        fallback = FastAPI()

        @fallback.get("/__import_error")
        def import_error():
            return Response(
                "Startup import failed in api/index.py\n\n=== Exception ===\n" + tb,
                media_type="text/plain",
                status_code=500,
            )

        @fallback.get("/{path:path}")
        def catchall(path: str):
            return Response(
                "Serverless import failed. Visit /__import_error for traceback.",
                media_type="text/plain",
                status_code=500,
            )

        return fallback


app = _build_app()
