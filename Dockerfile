FROM python:3.9-slim

WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force the correct Werkzeug version for Flask 2.2.3
RUN pip install --no-cache-dir werkzeug==2.2.3

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

# Copy the project files
COPY . .

# Create necessary directories
RUN mkdir -p data/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create a wrapper script for Cloud Run
RUN echo '#!/bin/bash' > /app/run.sh && \
    echo '# Process any existing products' >> /app/run.sh && \
    echo 'python run_pipeline.py --skip-scraping --skip-summarization || true' >> /app/run.sh && \
    echo '# Start the Flask API server directly with our dedicated script' >> /app/run.sh && \
    echo 'python start_flask_api.py' >> /app/run.sh && \
    chmod +x /app/run.sh

# Set default command
CMD ["/app/run.sh"]

# Cloud Run sets PORT environment variable which our start_flask_api.py script
# will read to bind to the correct port
