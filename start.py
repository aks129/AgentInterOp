#!/usr/bin/env python3

import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app, socketio

if __name__ == '__main__':
    # Use eventlet for Flask-SocketIO
    import eventlet
    eventlet.monkey_patch()
    
    print("Starting Multi-Agent Interoperability Demo...")
    print("Server will run on http://0.0.0.0:5000")
    
    # Run with eventlet server
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=True,
        use_reloader=False,
        log_output=True
    )