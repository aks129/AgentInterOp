#!/usr/bin/env python3
"""
Optimized server startup script for reduced resource usage
"""
import subprocess
import sys
import os

def main():
    """Start the server with optimized gunicorn settings"""
    cmd = [
        "gunicorn",
        "--bind", "0.0.0.0:5000",
        "--workers", "1",
        "--timeout", "60",
        "--preload",
        "--log-level", "error",
        "--worker-class", "sync",
        "main:app"
    ]
    
    print("Starting optimized server...")
    os.execvp("gunicorn", cmd)

if __name__ == "__main__":
    main()