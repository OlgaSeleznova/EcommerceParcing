"""
Content Enhancer Library

This library combines the product summarization and comparison functionality
for e-commerce product data, providing a cohesive organization for LLM-related features.
"""

# Import key functions from the llm_processor module
from content_enhancer.llm_processor import (
    LLMProcessor,
    process_products,
    generate_product_content
)

# Import key functions from the comparison module
from content_enhancer.comparison import (
    compare_products,
    get_top_rated_products
)

__all__ = [
    'LLMProcessor',
    'process_products',
    'generate_product_content',
    'compare_products',
    'get_top_rated_products'
]
