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
- **LLM Integration**: OpenAI API
- **API Framework**: Flask with REST API
- **Data Storage**: JSON files 

## Project Structure

```
EcommerceParcing/
├── README.md                   # Project documentation
├── requirements.txt            # Dependencies
├── config.py                   # Configuration settings
├── scraper/
│   ├── __init__.py
│   ├── main.py                 # Best Buy specific scraper
│   └── utils.py                # Scraping utilities
├── summarizer/
│   ├── __init__.py
│   ├── llm_processor.py        # LLM connection and prompt handling
│   └── comparison.py           # Product data enrichment logic
├── api/
│   ├── __init__.py
│   ├── flask_api.py            # Flask API application
│   ├── main.py                 # API entry point
├── data/                       # Directory for storing scraped and processed data 
│   ├── logs/                   # Directory for storing logs
├── run_pipeline.py             # Pipeline entry point
├── start_flask_api.py          # Script to start the Flask API server
├── Dockerfile                  # Dockerfile for containerization
├── cloudbuild.yaml             # Cloud Build configuration
├── ecommerce_parce/            # Python virtual environment directory
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/EcommerceParcing.git
```

2. Create a virtual environment and activate it:
```bash
python -m venv ecommerce_parce
source ecommerce_parce/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Set up environment variables:
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
### 3. Generate Product comparison
```bash
python -m content_enhancer.comparison
```
### 4. Start the API Server
```bash
python run_pipeline.py --skip-scraping --start-api
```

```bash
python run_pipeline.py --skip-scraping --skip-summarization --start-api
```

Access the API at http://127.0.0.1:8888

## API Endpoints

- `GET /products` - Get all products with their summaries
- `GET /products/{product_id}` - Get a specific product by ID
- `GET /products/comparison` - Get a comparison of the top 3 rated products

## Deployment

### Local Deployment with Docker

1. Build and run the Docker container:
```bash
docker-compose up -d
```

2. Access the API at http://localhost:8888

### Google Cloud Platform (GCP) Deployment

1. Install Google Cloud SDK:
```bash
# For macOS
brew install --cask google-cloud-sdk
```

2. Initialize the Google Cloud SDK:
```bash
gcloud init
```

3. Authenticate with Google Cloud:
```bash
gcloud auth login
```

4. Set GCP project:
```bash
gcloud config set project YOUR_PROJECT_ID
```

5. Enable required APIs:
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

6. Set OpenAI API key as a secret:
```bash
gcloud secrets create OPENAI_API_KEY --replication-policy=automatic
gcloud secrets versions add OPENAI_API_KEY --data-file=- # Enter your API key when prompted
```

7. Deploy to Cloud Run using Cloud Build:
```bash
gcloud builds submit --config=cloudbuild.yaml --substitutions=_OPENAI_API_KEY=YOUR_API_KEY
```

8. Access your deployed API at the URL provided in the Cloud Run console
cd EcommerceParcing
```


## Contributors

- Olga Seleznova
