"""
Scraper utility functions for the E-Commerce Scraping and LLM Summarization Pipeline.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

# Set up logger
logger = logging.getLogger(__name__)

def load_scraped_data(file_path: str) -> List[Dict]:
    """
    Load previously scraped data from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing scraped data
        
    Returns:
        A list of dictionaries containing product data
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return []
            
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} products from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {str(e)}")
        return []

def save_scraped_data(data: List[Dict], file_path: str) -> bool:
    """
    Save scraped data to a JSON file.
    
    Args:
        data: A list of dictionaries containing product data
        file_path: Path to save the data to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(data)} products to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {str(e)}")
        return False

def filter_products(products: List[Dict], **kwargs) -> List[Dict]:
    """
    Filter products based on the provided criteria.
    
    Args:
        products: A list of dictionaries containing product data
        **kwargs: Criteria to filter by (e.g., category='laptops')
        
    Returns:
        A filtered list of products
    """
    filtered_products = products
    
    for key, value in kwargs.items():
        if value is not None:
            filtered_products = [p for p in filtered_products if p.get(key) == value]
    
    return filtered_products

def get_categories(products: List[Dict]) -> List[str]:
    """
    Get a list of unique categories from the products.
    
    Args:
        products: A list of dictionaries containing product data
        
    Returns:
        A list of unique categories
    """
    return sorted(list(set(p.get('category', '') for p in products if p.get('category'))))

def get_product_by_id(products: List[Dict], product_id: str) -> Optional[Dict]:
    """
    Get a product by its ID.
    
    Args:
        products: A list of dictionaries containing product data
        product_id: The ID of the product to retrieve
        
    Returns:
        The product dictionary or None if not found
    """
    for product in products:
        if product.get('id') == product_id:
            return product
    return None

def print_product_summary(product: Dict) -> None:
    """
    Print a summary of a product.
    
    Args:
        product: A dictionary containing product data
    """
    print(f"\n=== {product.get('title', 'Unnamed Product')} ===")
    print(f"Price: {product.get('price', 'N/A')}")
    print(f"Rating: {product.get('rating', 'N/A')}")
    print(f"URL: {product.get('url', 'N/A')}")
    
    # Print a shortened description
    description = product.get('description', '')
    if description:
        if len(description) > 200:
            description = description[:197] + "..."
        print(f"\nDescription: {description}")
    
    # Print specifications (limited to 5)
    specs = product.get('specifications', {})
    if specs:
        print("\nSpecifications:")
        for i, (key, value) in enumerate(specs.items()):
            if i >= 5:
                print(f"... and {len(specs) - 5} more specifications")
                break
            print(f"  - {key}: {value}")
    print()
