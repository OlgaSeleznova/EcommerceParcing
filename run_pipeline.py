#!/usr/bin/env python
"""
Run the complete E-Commerce Scraping and LLM Summarization Pipeline.
"""
import os
import sys
import json
import logging
import argparse
import subprocess
# from summarizer.llm_processor import process_all_products
from content_enhancer.llm_processor import process_products
from content_enhancer.comparison import compare_products
# Import configuration
from config import LOGGING_CONFIG, DATA_PATHS

# Configure logging
os.makedirs(os.path.dirname(LOGGING_CONFIG["file"]), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pipeline")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="E-Commerce Scraping and LLM Summarization Pipeline")
    
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="Skip the scraping step and use existing scraped data"
    )
    
    parser.add_argument(
        "--skip-summarization",
        action="store_true",
        help="Skip the LLM summarization step and use existing processed data"
    )
    
    parser.add_argument(
        "--start-api",
        action="store_true",
        help="Start the Flask API server after processing"
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key to use for LLM processing"
    )
    return parser.parse_args()

# def run_scraper():
#     """Run the scraper to collect product data."""
#     logger.info("Starting web scraping process") 
    
#     try:
#         # Run the scraper module
#         subprocess.run([sys.executable, "scraper/main.py"], check=True)
        
#         # Check if the data was scraped successfully
#         if os.path.exists(DATA_PATHS["scraped_data"]):
#             with open(DATA_PATHS["scraped_data"], "r") as f:
#                 products = json.load(f)
                
#             logger.info(f"Successfully scraped {len(products)} products")
#             return True
#         else:
#             logger.error("No scraped data found after running scraper")
#             return False
            
#     except subprocess.CalledProcessError as e:
#         logger.error(f"Error running scraper: {str(e)}")
#         return False
#     except Exception as e:
#         logger.error(f"Unexpected error during scraping: {str(e)}")
#         return False

# def run_summarizer():
#     """Run the LLM summarizer to process product data."""
#     try:
#         # Import the summarizer function
        
        
#         # Process all products
#         processed_products = process_all_products()
        
#         if processed_products:
#             logger.info(f"Successfully processed {len(processed_products)} products with LLM")
#             return True
#         else:
#             logger.error("No products were processed by the LLM")
#             return False
            
#     except Exception as e:
#         logger.error(f"Error during LLM summarization: {str(e)}")
#         return False

def run_content_enhancer(run_comparison=True):
    """Run the content enhancer to process and compare product data."""
    logger.info("Running content enhancer")
    
    try:

        
        # Process the products
        processed_products = process_products(
            input_path=DATA_PATHS["scraped_data"],
            output_path=DATA_PATHS["processed_data"],
        )
        
        if not processed_products:
            logger.error("Failed to process products")
            return False
            
        logger.info(f"Successfully processed {len(processed_products)} products")
        
        # Run comparison if requested
        if run_comparison:
            logger.info("Running product comparison")
            comparison_data = compare_products()
            if comparison_data:
                logger.info("Successfully generated product comparison")
            else:
                logger.warning("Failed to generate product comparison")
        
        return True
            
    except Exception as e:
        logger.error(f"Error running content enhancer: {str(e)}")
        return False

def start_api_server():
    """Start the Flask API server."""
    logger.info("Starting Flask API server")
    
    try:
        # Import the Flask API server
        from api.flask_api import start_flask_api
        
        # Start the Flask API server
        start_flask_api()
        return True
        
    except Exception as e:
        logger.error(f"Error starting Flask API server: {str(e)}")
        return False

def main():
    """Main function to run the complete pipeline."""
    args = parse_args()
    
    logger.info("Starting E-Commerce Scraping and LLM Summarization Pipeline")
    
    # Step 1: Run the scraper (if not skipped)
    if not args.skip_scraping:
        if not run_scraper():
            logger.error("Scraping failed, aborting pipeline")
            return 1
    else:
        logger.info("Skipping scraping step")
        
        # Check if scraped data exists
        if not os.path.exists(DATA_PATHS["scraped_data"]):
            logger.error(f"No scraped data found at {DATA_PATHS['scraped_data']}")
            logger.error("Cannot proceed without scraped data")
            return 1
    
    # Step 2: Run the content enhancer (if not skipped)
    if not args.skip_summarization:
        # Add API key from command line if provided (overrides .env file)
        if args.api_key:
            os.environ["OPENAI_API_KEY"] = args.api_key
            logger.info("Using OpenAI API key from command line arguments")
        elif os.getenv("OPENAI_API_KEY"):
            logger.info("Using OpenAI API key from environment variables")
        else:
            logger.warning("No OpenAI API key found. Please set OPENAI_API_KEY in .env file or provide via --api-key argument")
        
        # Run content enhancer with comparison
        if not run_content_enhancer(run_comparison=True):
            logger.error("Content enhancement failed, aborting pipeline")
            return 1
    else:
        logger.info("Skipping content enhancement step")
        
        # Check if processed data exists
        if not os.path.exists(DATA_PATHS["processed_data"]):
            logger.warning(f"No processed data found at {DATA_PATHS['processed_data']}")
            logger.warning("API will serve raw scraped data instead")
    
    # Step 3: Start the API server (if requested)
    if args.start_api:
        if not start_api_server():
            logger.error("Failed to start Flask API server")
            return 1
    else:
        logger.info("Pipeline completed successfully")
        logger.info(f"To start the Flask API server, run: python start_flask_api.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
