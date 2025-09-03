#!/usr/bin/env python3

import uvicorn
from app.main import app

if __name__ == "__main__":
    # Start with uvicorn (ASGI server) - compatible with FastAPI
    print("Starting Multi-Agent Interoperability Demo with FastAPI")
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=5000,
        log_level="info",
        access_log=True
    )