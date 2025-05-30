#!/usr/bin/env python
"""
Command-line interface for product comparison.
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LOGGING_CONFIG
from comparison.compare_products import compare_products

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("comparison_cli")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Product Comparison Tool")
    
    parser.add_argument(
        "--use-mock",
        action="store_true",
        help="Use mock data instead of real LLM API calls"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    logger.info("Starting product comparison")
    
    # Run the comparison
    comparison_data = compare_products(use_mock=args.use_mock)
    
    if not comparison_data:
        logger.error("Failed to generate product comparison")
        return 1
    
    logger.info("Product comparison completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
