#!/usr/bin/env python
"""
Simple script to start the Flask API server.
Supports both local development and Cloud Run deployment.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.flask_api import app
from config import API_CONFIG

def main():
    """Start the Flask API server."""
    # Get port from environment variable for Cloud Run compatibility
    port = int(os.environ.get("PORT", API_CONFIG["port"]))
    host = "0.0.0.0"  # Bind to all interfaces for cloud environments
    
    print(f"Starting Flask API server at http://{host}:{port}")
    print("Press Ctrl+C to stop the server")
    
    # Start the Flask API server with explicit host and port
    app.run(host=host, port=port, debug=API_CONFIG["debug"])

if __name__ == "__main__":
    main()
