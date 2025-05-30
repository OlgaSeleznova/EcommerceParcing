"""
REST API for serving processed product data using Flask.
"""
import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from flask import Flask, jsonify, request, abort
from flask_cors import CORS

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_CONFIG, DATA_PATHS, LOGGING_CONFIG

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("flask_api")

# Create Flask app
app = Flask(__name__)

# Add CORS
CORS(app, resources={r"/*": {"origins": API_CONFIG["cors_origins"]}})

def load_products(file_path: str = DATA_PATHS["processed_data"]) -> List[Dict[str, Any]]:
    """
    Load products from the processed data file.
    
    Args:
        file_path (str): Path to the processed data file
        
    Returns:
        List[Dict[str, Any]]: List of processed products
    """
    try:
        if not os.path.exists(file_path):
            # Try to load from scraped data if processed data doesn't exist
            file_path = DATA_PATHS["scraped_data"]
            if not os.path.exists(file_path):
                logger.error(f"No product data found at {file_path}")
                return []
                
        with open(file_path, 'r') as f:
            products = json.load(f)
            
        logger.info(f"Loaded {len(products)} products from {file_path}")
        return products
        
    except Exception as e:
        logger.error(f"Error loading products from {file_path}: {str(e)}")
        return []

@app.route('/')
def root():
    """Root endpoint with API information."""
    return jsonify({
        "message": "E-Commerce Product API (Flask)",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/products", "method": "GET", "description": "Get all products"},
            {"path": "/products/<product_id>", "method": "GET", "description": "Get a product by ID"},
            {"path": "/products/category/<category>", "method": "GET", "description": "Get products by category"}
        ]
    })

@app.route('/products')
def get_products():
    """
    Get all products with optional filtering and pagination.
    
    Query Parameters:
        limit: Maximum number of products to return
        offset: Number of products to skip
        category: Filter products by category
        
    Returns:
        JSON: Products and metadata
    """
    # Get query parameters
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    category = request.args.get('category', default=None, type=str)
    
    products = load_products()
    
    # Filter by category if specified
    if category:
        products = [p for p in products if p.get("category", "").lower() == category.lower()]
    
    # Calculate total count and paginate
    total_count = len(products)
    products = products[offset:offset + limit]
    
    return jsonify({
        "products": products,
        "metadata": {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "count": len(products)
        }
    })

@app.route('/products/<product_id>')
def get_product(product_id):
    """
    Get a product by ID.
    
    Args:
        product_id (str): ID of the product to get
        
    Returns:
        JSON: Product data
    """
    products = load_products()
    
    # Find the product with the given ID
    for product in products:
        if product.get("id") == product_id:
            return jsonify(product)
    
    # If no product is found, return 404
    abort(404, description=f"Product with ID '{product_id}' not found")

@app.route('/products/category/<category>')
def get_products_by_category(category):
    """
    Get products by category.
    
    Args:
        category (str): Category to filter by
        
    Query Parameters:
        limit: Maximum number of products to return
        offset: Number of products to skip
        
    Returns:
        JSON: Products and metadata
    """
    # Get query parameters
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    products = load_products()
    
    # Filter products by category
    filtered_products = [p for p in products if p.get("category", "").lower() == category.lower()]
    
    # Calculate total count and paginate
    total_count = len(filtered_products)
    filtered_products = filtered_products[offset:offset + limit]
    
    return jsonify({
        "category": category,
        "products": filtered_products,
        "metadata": {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "count": len(filtered_products)
        }
    })

def start_flask_api():
    """Start the Flask API server."""
    app.run(
        host=API_CONFIG["host"],
        port=API_CONFIG["port"], 
        debug=API_CONFIG["debug"]
    )

if __name__ == "__main__":
    # Start the Flask API server
    start_flask_api()
