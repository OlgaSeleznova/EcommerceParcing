#!/usr/bin/env python
"""
Command-line interface for the LLM Summarization module.
"""
import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_PATHS, LOGGING_CONFIG, LLM_CONFIG
from summarizer.llm_processor import process_all_products, LLMProcessor

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_summarizer_cli")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="LLM Summarization Tool for E-Commerce Products")
    
    parser.add_argument(
        "--input", "-i",
        default=DATA_PATHS["scraped_data"],
        help=f"Path to input JSON file (default: {DATA_PATHS['scraped_data']})"
    )
    
    parser.add_argument(
        "--output", "-o",
        default=DATA_PATHS["processed_data"],
        help=f"Path to output JSON file (default: {DATA_PATHS['processed_data']})"
    )
    
    parser.add_argument(
        "--provider", "-p",
        choices=["Ollama", "HUGGINGFACE"],
        default="Ollama",
        help="LLM provider to use (default: Ollama)"
    )
    
    parser.add_argument(
        "--single", "-s",
        action="store_true",
        help="Process a single product (specify product ID with --id)"
    )
    
    parser.add_argument(
        "--id",
        help="ID of product to process (required with --single)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()

def process_single_product(product_id, input_path, output_path, llm_provider):
    """Process a single product by ID."""
    try:
        # Load products from the input file
        with open(input_path, 'r') as f:
            products = json.load(f)
        
        # Find the product with the given ID
        target_product = None
        for product in products:
            if product.get("id") == product_id:
                target_product = product
                break
        
        if not target_product:
            logger.error(f"Product with ID '{product_id}' not found")
            return False
        
        # Initialize the LLM processor
        processor = LLMProcessor(llm_provider=llm_provider)
        
        # Process the product
        processed_product = processor.process_product(target_product)
        
        logger.info(f"Successfully processed product: {product_id}")
        
        # If an output file exists, update just this product
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r') as f:
                    processed_products = json.load(f)
                
                # Update or add the processed product
                updated = False
                for i, product in enumerate(processed_products):
                    if product.get("id") == product_id:
                        processed_products[i] = processed_product
                        updated = True
                        break
                
                if not updated:
                    processed_products.append(processed_product)
                
                with open(output_path, 'w') as f:
                    json.dump(processed_products, f, indent=2)
                
            except Exception as e:
                logger.error(f"Error updating output file: {str(e)}")
                # Fall back to creating a new file with just this product
                with open(output_path, 'w') as f:
                    json.dump([processed_product], f, indent=2)
        else:
            # Create a new output file with just this product
            with open(output_path, 'w') as f:
                json.dump([processed_product], f, indent=2)
        
        logger.info(f"Saved processed product to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing product {product_id}: {str(e)}")
        return False

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Process products
    if args.single:
        if not args.id:
            logger.error("Product ID required with --single option")
            return 1
        
        success = process_single_product(args.id, args.input, args.output, args.provider)
        return 0 if success else 1
    else:
        processed_products = process_all_products(
            input_path=args.input,
            output_path=args.output,
            llm_provider=args.provider
        )
        
        return 0 if processed_products else 1

if __name__ == "__main__":
    sys.exit(main())
