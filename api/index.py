import os, sys, traceback
os.environ.setdefault("APP_ENV", "vercel")
try:
    from app.main import app as _fastapi_app
    app = _fastapi_app
except Exception as e:
    from fastapi import FastAPI, Response
    tb = "".join(traceback.format_exception(e))
    print("=== VERCEL IMPORT FAILURE ===", file=sys.stderr, flush=True)
    print(tb, file=sys.stderr, flush=True)
    app = FastAPI()
    @app.get("/__import_error")
    def import_error():
        return Response(("Startup import failed in api/index.py\n\n=== Exception ===\n" + tb),
                        media_type="text/plain", status_code=500)
    @app.get("/{path:path}")
    def catchall(path: str):
        return Response(
            "Serverless import failed. Visit /__import_error for traceback.",
            media_type="text/plain",
            status_code=500,
        )