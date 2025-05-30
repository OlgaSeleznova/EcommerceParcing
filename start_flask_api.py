#!/usr/bin/env python
"""
Simple script to start the Flask API server.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.flask_api import start_flask_api
from config import API_CONFIG

def main():
    """Start the Flask API server."""
    flask_port = API_CONFIG["port"] + 1
    print(f"Starting Flask API server at http://{API_CONFIG['host']}:{flask_port}")
    print("Press Ctrl+C to stop the server")
    
    # Start the Flask API server
    start_flask_api()

if __name__ == "__main__":
    main()
