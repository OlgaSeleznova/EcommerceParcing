#!/usr/bin/env python
"""
Main entry point for the LLM Summarization module.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_PATHS, LOGGING_CONFIG
from summarizer.llm_processor import process_all_products

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_summarizer_main")

def main():
    """
    Main function to run the LLM Summarization pipeline.
    """
    logger.info("Starting LLM Summarization pipeline")
    
    # Process all products
    processed_products = process_all_products()
    
    if processed_products:
        logger.info(f"Successfully processed {len(processed_products)} products")
        
        # Output a sample of the processed products
        if len(processed_products) > 0:
            sample = processed_products[0]
            logger.info("\nSample processed product:")
            logger.info(f"ID: {sample.get('id')}")
            logger.info(f"Title: {sample.get('title')}")
            logger.info(f"Summary: {sample.get('summary')}")
            logger.info(f"Tagline: {sample.get('tagline')}")
            logger.info("Highlights:")
            for highlight in sample.get('highlights', []):
                logger.info(f"- {highlight}")
    else:
        logger.error("No products were processed")
    
    return 0 if processed_products else 1

if __name__ == "__main__":
    sys.exit(main())
