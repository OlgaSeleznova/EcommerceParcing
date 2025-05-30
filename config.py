"""
Configuration settings for the E-Commerce Scraping and LLM Summarization Pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
            },
            {
                "slug": "TV",
                "name": "Televisions",
                "url": "https://www.bestbuy.ca/en-ca/category/televisions/20009"
            },
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
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 150,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
    # Prompt templates
    "PROMPTS": {
        "summary": "You are an experienced Marketing specialist. Your task is to maximize sales for the product. Please generate concise 2–3 sentence summary using the following information: Product descrintion {description}, key features {features}.",
        "tagline": "You are a marketing copywriter. Based on the following product description {description} and key features {features}, generate a catchy, concise tagline (no more than 10 words) that communicates the product's main benefit. Respond to the question: 'What a user can do best with this product?'. Finish by mentioning consicely the product name. For example, 'Unleash limitless creativity with Surface Pro's AI-powered versatility.' 'Unleash Power and Portability with ASUS Vivobook 16.' 'Elevate Your Efficiency with Zenbook 14 OLED.',",
        "comparison": ""
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
