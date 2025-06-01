"""
Configuration settings for the E-Commerce Scraping and LLM Summarization Pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from config.env file
load_dotenv(dotenv_path='config.env')

# Ensure the data directory exists
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Ensure the logs directory exists
LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Scraper Configuration
SCRAPER_CONFIG = {
    "BestBuy": {
        "base_url": "https://bestbuy.ca",
        "search_url": "https://www.bestbuy.ca/en-ca/search?searchTerm={query}",
        "categories": [
            {
                "slug": "Laptops",
                "name": "Laptops & MacBooks",
                "url": "https://www.bestbuy.ca/en-ca/category/laptops-macbooks/20352"
            }
        ],
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "en-US,en;q=0.9",
            },
        "request_delay": 2,
        "max_retries": 3,
    },
}


# LLM Configuration
LLM_CONFIG = {
    # OpenAI configuration
    "OpenAI": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 150,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
    # Prompt templates
    "PROMPTS": {
        "summary": {
            "system_msg": "You are an experienced Marketing specialist.",
            "prompt": """Your task is to maximize sales for the product. Please generate concise 2–3 sentence summary using the following information: 
            Product description {description}, key features {features}."""
        },
        "tagline": {
            "system_msg": "You are a marketing copywriter. You do not use the word Tagline in your response",
            "prompt": """Please, generate a catchy, concise tagline, based on the following product description {description}, key features {features}, and title {title}. 
                Respond to the question: 'What a user can do best with this product?'. Finish by mentioning concisely the product name. Use not more than 10 words.
                For example, 'Unleash limitless creativity with Surface Pro's AI-powered versatility.', 
                'Elevate Your Efficiency with Zenbook 14 OLED.'
                """
        },
        "product_comparison": {
            "questions": {
                "system_msg": "You are a product comparison specialist.",
                "prompt": """Based on the following product descriptions, generate 5 important comparison criteria that would help a customer decide which product is best.
                        Frame each criterion as a question that asks which product is best for that specific criterion.
                        
                        Products:
                        {products}
                        
                        Output exactly 5 comparison criteria questions, one per line, without numbering or additional text."""
            },
            "responses": {
                "system_msg": "You are a product comparison specialist.",
                "prompt": """Based on the following product descriptions, 
                            determine which product is best for the given criterion. Explain your reasoning in 2-3 sentences.
                            Criterion: {criterion}
                            Products:
                            {products}
                            First state which product is best for this criterion (Product 1, Product 2, or Product 3).
                            Then explain why in 2-3 sentences."""
            }
        }
    }
}

# API Configuration
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8888,  
    "debug": True,
    "cors_origins": ["*"], 
    "cors_methods": ["GET"],
}

# Data paths
DATA_PATHS = {
    "scraped_data": str(DATA_DIR / "scraped_products.json"),
    "processed_data": str(DATA_DIR / "processed_products.json"),
    "logs": str(LOGS_DIR),
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": str(LOGS_DIR / "app.log"),
}
