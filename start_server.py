#!/usr/bin/env python3
"""
Startup script for the Multi-Agent Interoperability Demo
"""
import signal
import sys
import uvicorn
from app.main import app

def signal_handler(sig, frame):
    print('Received signal to shut down...')
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Multi-Agent Interoperability Demo with FastAPI")
    
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=5000,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)