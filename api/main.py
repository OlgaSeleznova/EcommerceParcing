#!/usr/bin/env python
"""
Main entry point for the API server.
"""
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_CONFIG, LOGGING_CONFIG

# Local import (without using the api package name)
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from api import start_api

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_main")

def main():
    """Main function to start the API server."""
    logger.info("Starting API server")
    logger.info(f"API will be available at http://{API_CONFIG['host']}:{API_CONFIG['port']}")
    
    # Start the API server
    start_api()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
