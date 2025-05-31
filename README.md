# E-Commerce Scraping and LLM Summarization Pipeline

A Python-based pipeline that scrapes product data from Best Buy, generates AI-powered summaries using LLMs, and serves the processed data through a REST API.

## Project Objective

This project implements a data pipeline that:

1. Scrapes product data from Best Buy's public website
2. Uses a Large Language Model to generate marketing content for each product:
   - Concise product summaries
   - Catchy taglines
   - Product comparison
3. Serves the enriched product data through a REST API

## Technology Stack

- **Language**: Python 3.9+
- **Web Scraping**: Playwright
- **LLM Integration**: OpenAI API, with optional support for Hugging Face or local LLMs
- **API Framework**: Flask
- **Data Storage**: JSON files (can be extended to databases)

## Project Structure

```
EcommerceParcing/
├── README.md                   # Project documentation
├── requirements.txt            # Dependencies
├── config.py                   # Configuration settings
├── scraper/
│   ├── __init__.py
│   ├── bestbuy_scraper.py      # Best Buy specific scraper
│   └── utils.py                # Scraping utilities
├── summarizer/
│   ├── __init__.py
│   ├── llm_client.py           # LLM connection and prompt handling
│   └── product_enhancer.py     # Product data enrichment logic
├── api/
│   ├── __init__.py
│   ├── flask_api.py            # Flask API application
│   ├── models.py               # Data models
│   └── routes.py               # API endpoints
└── data/                       # Directory for storing scraped and processed data
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/EcommerceParcing.git
cd EcommerceParcing
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate # on MacOS
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Set up your environment variables:
```bash
# Create a .env file with your API keys
echo "OPENAI_API_KEY=your_key_here" > .env
```

## Usage

### 1. Run the Scraper

```bash
python -m scraper.bestbuy_scraper --category laptops --count 10
```

### 2. Generate Summaries

```bash
python -m content_enhancer.llm_processor
```

### 3. Start the API Server
```bash
python run_pipeline.py --skip-scraping --start-api

python run_pipeline.py --skip-scraping --skip-summarization --start-api
```
Access the API at http://127.0.0.1:8888

## API Endpoints

- `GET /products` - Get all products with their summaries
- `GET /products/{product_id}` - Get a specific product by ID
- `GET /products/comparison` - Get a comparison of the top 3 rated products


## Contributors

- Olga Seleznova
