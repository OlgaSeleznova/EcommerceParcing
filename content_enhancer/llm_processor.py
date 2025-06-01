"""
LLM Processing module for generating product summaries and taglines.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Import config
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_CONFIG, DATA_PATHS, LOGGING_CONFIG

# Load environment variables from config.env file
load_dotenv(dotenv_path='config.env')

# Set up logging with unique filename based on timestamp
def setup_logger(name="llm_processor"):
    """Set up logger with unique filename based on timestamp."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
    
    # Create formatter
    formatter = logging.Formatter(LOGGING_CONFIG["format"])
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
    console_handler.setFormatter(formatter)
    
    # Create file handler with unique filename
    log_file = LOGGING_CONFIG.get("file")
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)
        
        # Add timestamp to log filename to create unique logs for each run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"content_enhancer_{timestamp}.log"
        log_path = os.path.join(log_dir, log_filename)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_path}")
    
    # Add console handler
    logger.addHandler(console_handler)
    
    # Prevent logs from being propagated to the root logger
    logger.propagate = False
    
    return logger

# Initialize logger
logger = setup_logger()

class LLMProcessor:
    """Handles processing product data through LLM to generate summaries and taglines."""
    
    def __init__(self):
        """
        Initialize the LLM processor.
        """
        self.config = LLM_CONFIG["OpenAI"]
        self.prompts = LLM_CONFIG["PROMPTS"]
        
        # Configure OpenAI client with API key from environment variables
        api_key = os.getenv("OPENAI_API_KEY") or self.config.get("api_key")
        if not api_key:
            logger.warning("No OpenAI API key found in environment variables or config")
            
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info(f"Initialized LLM processor with provider: OpenAI")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
    
    def _openai_request(self, prompt: str, system_msg: str = None, max_retries: int = 1) -> str:
        """
        Make a request to the OpenAI API with validation and retry logic.
        
        Args:
            prompt (str): The prompt to send to the API
            system_msg (str): Optional system message override
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            str: The response from the API or empty string on failure
        """
        if not prompt:
            logger.error("Empty prompt provided to OpenAI API")
            return ""
            
        retries = 0
        while retries <= max_retries:
            try:
                # Prepare messages with system message and user prompt
                system_content = system_msg or "You are a helpful assistant that generates content for e-commerce products."
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ]
                
                # Check if client was initialized properly
                if not self.client:
                    logger.error("OpenAI client not initialized properly")
                    return ""
                    
                # Make the request without proxies parameter
                response = self.client.chat.completions.create(
                    model=self.config["model"],
                    messages=messages,
                    temperature=self.config["temperature"],
                    max_tokens=self.config["max_tokens"]
                )
                
                # Extract the content from the response
                if response and hasattr(response, 'choices') and len(response.choices) > 0:
                    result = response.choices[0].message.content.strip()
                    
                    # Validate the result isn't empty or an error message
                    if result and not result.lower().startswith("error"):
                        return result
                    else:
                        logger.warning(f"Empty or error response from OpenAI: {result}")
                else:
                    logger.warning("Invalid response structure from OpenAI API")
                    
                # If we got here, the response wasn't valid - retry if possible
                if retries < max_retries:
                    retries += 1
                    logger.warning(f"Retrying OpenAI request (attempt {retries})")
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error making request to OpenAI API: {str(e)}")
                if retries < max_retries:
                    retries += 1
                    logger.warning(f"Retrying OpenAI request after error (attempt {retries})")
                else:
                    break
        
        # If all retries failed
        return ""
    
    def generate_summary(self, description: str, features: List[str]) -> str:
        """
        Generate a concise 2-3 sentence summary for a product.
        
        Args:
            description (str): Product description
            features (List[str]): List of product features
            
        Returns:
            str: Generated summary
        """
        # Format product information
        feature_text = "\n".join([f"- {feature}" for feature in features])
        
        # Get system message and prompt template
        summary_config = self.prompts["summary"]
        system_msg = summary_config["system_msg"]
        prompt_template = summary_config["prompt"]
        
        # Construct the prompt
        prompt = prompt_template.format(
            description=description,
            features=feature_text
        )
        
        summary = self._openai_request(prompt, system_msg=system_msg)
        
        return summary
    
    def generate_tagline_and_highlights(self, description: str, features: List[str], title: str = "") -> Dict[str, Any]:
        """
        Generate a tagline and bullet-point highlights for a product using the provided title.
        
        Args:
            description (str): Product description
            features (List[str]): List of product features
            title (str, optional): Product title to incorporate into the tagline generation
            
        Returns:
            Dict[str, Any]: Dictionary containing tagline and highlights
        """
        if not description and not features:
            logger.warning("Empty product description and features provided")
            return {"tagline": "", "highlights": []}
            
        # Format product information
        feature_text = "\n".join([f"- {feature}" for feature in features]) if features else "No features provided."
        
        # Get system message and prompt template
        tagline_config = self.prompts["tagline"]
        system_msg = tagline_config["system_msg"]
        prompt_template = tagline_config["prompt"]
        
        # Construct the prompt with explicit instructions for format and include title if provided
        # Include title directly in format() call to match the updated prompt template
        prompt = prompt_template.format(
            description=description or "No description provided.",
            features=feature_text,
            title=title or "the product"
        ) + "\n\nIMPORTANT: Please format your response with: \n1. Tagline: followed by a catchy tagline that incorporates the product title\n2. Highlights: A bulleted list of highlights using '-' at the start of each bullet point."
        
        response = self._openai_request(prompt, system_msg=system_msg, max_retries=2)
        
        # Parse the response to extract tagline and highlights
        try:
            if not response:
                logger.error("Empty response from OpenAI for tagline generation")
                return {"tagline": "", "highlights": []}
                
            lines = response.strip().split('\n')
            tagline = ""
            highlights = []
            
            # Enhanced parsing to handle different formats
            for i, line in enumerate(lines):
                line = line.strip()
                # Extract tagline - handle various formats
                if line.lower().startswith("tagline:") or line.lower().startswith("tagline -"):
                    tagline = line.split(":", 1)[1].strip() if ":" in line else line.split("-", 1)[1].strip()
                # If first line and no explicit tagline marker, assume it's the tagline
                elif i == 0 and not tagline and not line.startswith("-"):
                    tagline = line
                
                # Extract highlights
                if line.startswith("-") and len(line) > 1:
                    highlight_text = line[1:].strip()
                    if highlight_text and not highlight_text.lower().startswith("tagline"):
                        highlights.append(highlight_text)
            
            # Fallback: if no structured highlights found but content exists after tagline
            if not highlights and len(lines) > 1 and tagline:
                non_tagline_lines = [l for l in lines if not l.lower().startswith("tagline") and l.strip()]
                if non_tagline_lines:
                    # Use remaining content as single highlight if no bullet structure
                    highlights = [" ".join(non_tagline_lines).strip()]
            
            result = {
                "tagline": tagline.strip(),
                "highlights": [h for h in highlights if h.strip()]
            }
            
            # Log parsing results
            logger.debug(f"Parsed tagline: '{result['tagline']}'")
            logger.debug(f"Parsed {len(result['highlights'])} highlights")
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing LLM response for tagline: {str(e)}")
            # In case of error, try to salvage any content
            if response:
                lines = response.split('\n')
                return {
                    "tagline": lines[0] if lines else response[:50],
                    "highlights": lines[1:] if len(lines) > 1 else []
                }
            return {"tagline": "", "highlights": []}
    
    def process_product(self, product: Dict[str, Any], max_retries: int = 2) -> Dict[str, Any]:
        """
        Process a single product through the LLM pipeline.
        
        Args:
            product (Dict[str, Any]): Product data dictionary
            max_retries (int): Maximum number of retries for failed generations
            
        Returns:
            Dict[str, Any]: Processed product with LLM-generated content
        """
        # Skip processing if the product is already processed with valid content
        if (product.get("summary") and product.get("tagline") and product.get("highlights") and 
            len(product.get("summary", "")) > 0 and 
            len(product.get("tagline", "")) > 0 and 
            len(product.get("highlights", [])) > 0):
            logger.info(f"Product {product.get('id', 'unknown')} already processed with valid content, skipping")
            return product
        
        # Extract product information
        description = product.get("description", "")
        features = product.get("features", [])
        title = product.get("title", "")
        
        # Generate summary with validation and retry
        logger.info(f"Generating summary for product {product.get('id', 'unknown')}")
        summary = ""
        retries = 0
        while not summary and retries <= max_retries:
            if retries > 0:
                logger.warning(f"Retrying summary generation (attempt {retries})")
            summary = self.generate_summary(description, features)
            if not summary:
                logger.warning("Generated summary is empty, retrying")
                retries += 1
        
        if not summary:
            logger.error(f"Failed to generate valid summary for product {product.get('id', 'unknown')} after {max_retries} retries")
            summary = "Product summary unavailable."
            
        product["summary"] = summary
        
        # Generate tagline and highlights with validation and retry
        logger.info(f"Generating tagline and highlights for product {product.get('id', 'unknown')}")
        tagline_data = {"tagline": "", "highlights": []}
        retries = 0
        while (not tagline_data["tagline"] or not tagline_data["highlights"]) and retries <= max_retries:
            if retries > 0:
                logger.warning(f"Retrying tagline generation (attempt {retries})")
            tagline_data = self.generate_tagline_and_highlights(description, features, title)
            if not tagline_data["tagline"] or not tagline_data["highlights"]:
                logger.warning("Generated tagline or highlights are empty, retrying")
                retries += 1
                
        # Ensure we have at least some content even after failed retries
        if not tagline_data["tagline"]:
            logger.error(f"Failed to generate valid tagline for product {product.get('id', 'unknown')} after {max_retries} retries")
            tagline_data["tagline"] = "Product tagline unavailable."
            
        if not tagline_data["highlights"]:
            logger.error(f"Failed to generate valid highlights for product {product.get('id', 'unknown')} after {max_retries} retries")
            tagline_data["highlights"] = ["Product highlights unavailable."]
        
        product["tagline"] = tagline_data["tagline"]
        product["highlights"] = tagline_data["highlights"]
        
        # Log validation results
        logger.info(f"Validation complete for product {product.get('id', 'unknown')}:")
        logger.info(f"  Summary length: {len(product['summary'])} characters")
        logger.info(f"  Tagline length: {len(product['tagline'])} characters")
        logger.info(f"  Highlights count: {len(product['highlights'])} items")
        
        return product

def process_products(input_path: Optional[str] = None, 
                    output_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Process all products in the input file through the LLM pipeline.
    
    Args:
        input_path (Optional[str]): Path to the input JSON file
        output_path (Optional[str]): Path to save the processed products
        
    Returns:
        List[Dict[str, Any]]: List of processed products
    """
    # Set default paths if not provided
    input_path = input_path or DATA_PATHS["scraped_data"]
    output_path = output_path or DATA_PATHS["processed_data"]
    
    # Check if input file exists
    if not os.path.exists(input_path):
        logger.error(f"Input file not found at {input_path}")
        return []
    
    # Load products from input file
    try:
        with open(input_path, 'r') as f:
            products = json.load(f)
        logger.info(f"Loaded {len(products)} products from {input_path}")
    except Exception as e:
        logger.error(f"Error loading products from {input_path}: {str(e)}")
        return []
    
    # Initialize LLM processor
    processor = LLMProcessor()
    
    # Process each product
    processed_products = []
    for i, product in enumerate(products):
        logger.info(f"Processing product {i+1}/{len(products)}")
        processed_product = processor.process_product(product)
        processed_products.append(processed_product)
    
    # Save processed products
    if output_path:
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(processed_products, f, indent=2)
            logger.info(f"Saved {len(processed_products)} processed products to {output_path}")
        except Exception as e:
            logger.error(f"Error saving processed products to {output_path}: {str(e)}")
    
    return processed_products

# Alias for backwards compatibility
generate_product_content = process_products

if __name__ == "__main__":
    # Process all products with default settings
    process_products()
