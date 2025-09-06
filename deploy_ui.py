#!/usr/bin/env python3
"""
Script to deploy React UI build to Flask static directory
"""
import os
import shutil
import sys
from pathlib import Path

def deploy_react_ui(react_build_path):
    """Deploy React build to Flask static directory"""
    
    # Paths
    react_build = Path(react_build_path)
    flask_static = Path("app/web/static")
    
    # Validate React build directory
    if not react_build.exists():
        print(f"❌ React build directory not found: {react_build}")
        return False
    
    if not (react_build / "index.html").exists():
        print(f"❌ index.html not found in: {react_build}")
        return False
    
    # Backup existing static files
    backup_dir = Path("app/web_backup_" + str(int(time.time())))
    if flask_static.exists():
        print(f"📦 Backing up existing static files to: {backup_dir}")
        shutil.copytree(flask_static, backup_dir)
    
    # Clear and recreate static directory
    if flask_static.exists():
        shutil.rmtree(flask_static)
    flask_static.mkdir(parents=True, exist_ok=True)
    
    # Copy React build files
    print(f"🚀 Copying React build from: {react_build}")
    for item in react_build.iterdir():
        if item.is_file():
            shutil.copy2(item, flask_static)
            print(f"   📄 {item.name}")
        elif item.is_dir():
            shutil.copytree(item, flask_static / item.name)
            print(f"   📁 {item.name}/")
    
    print(f"✅ React UI deployed successfully!")
    print(f"🌐 Start the backend and visit: http://localhost:5000")
    return True

if __name__ == "__main__":
    import time
    
    if len(sys.argv) != 2:
        print("Usage: python deploy_ui.py <path-to-react-build-directory>")
        print("Example: python deploy_ui.py ../my-react-app/build")
        sys.exit(1)
    
    react_build_path = sys.argv[1]
    success = deploy_react_ui(react_build_path)
    sys.exit(0 if success else 1)