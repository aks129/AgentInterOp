import os, sys, traceback
os.environ.setdefault("APP_ENV", "vercel")  # used to switch to /tmp, etc.

try:
    # IMPORTANT: app must be importable without side effects
    from app.main import app as _fastapi_app
    app = _fastapi_app
except Exception as e:
    # Fallback ASGI app that returns the traceback so Vercel doesn't hide it
    from fastapi import FastAPI, Response
    tb = "".join(traceback.format_exception(e))
    print("=== VERCEL IMPORT FAILURE ===", file=sys.stderr, flush=True)
    print(tb, file=sys.stderr, flush=True)

    app = FastAPI()

    @app.get("/__import_error")
    def import_error():
        return Response(
            content=("Startup import failed in api/index.py\n\n=== Exception ===\n" + tb),
            media_type="text/plain",
            status_code=500,
        )

    @app.get("/{path:path}")
    def catchall(path: str):
        return Response(
            content=(
                "Serverless import failed. Visit /__import_error to see traceback.\n\n"
                "Fix app.main (or its imports) and redeploy."
            ),
            media_type="text/plain",
            status_code=500,
        )