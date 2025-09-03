#!/usr/bin/env python3

import subprocess
import sys
import os

def main():
    # Change to the correct directory
    os.chdir('/home/runner/workspace')
    
    # Run uvicorn with the correct command
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    
    print("Starting FastAPI server with uvicorn...")
    print(f"Command: {' '.join(cmd)}")
    
    # Run the server
    subprocess.run(cmd)

if __name__ == "__main__":
    main()