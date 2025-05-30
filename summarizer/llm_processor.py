"""
LLM Processing module for generating product summaries and taglines.
"""
import os
import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
import openai

# Import config
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_CONFIG, DATA_PATHS, LOGGING_CONFIG

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG["file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_summarizer")

class LLMProcessor:
    """
    Handles processing product data through LLM to generate summaries and taglines.
    """
    def __init__(self, llm_provider: str = "OpenAI"):
        """
        Initialize the LLM processor.
        
        Args:
            llm_provider (str): Provider to use for LLM processing ('OpenAI', 'Ollama', or 'HUGGINGFACE')
        """
        self.provider = llm_provider
        self.config = LLM_CONFIG[llm_provider]
        self.prompts = LLM_CONFIG["PROMPTS"]
        
        # Configure OpenAI API key if using OpenAI
        if llm_provider == "OpenAI" and self.config.get("api_key"):
            openai.api_key = self.config["api_key"]
        
        logger.info(f"Initialized LLM processor with provider: {self.provider}")

    # def _ollama_request(self, prompt: str) -> str:
    #     """
    #     Make a request to the Ollama API.
        
    #     Args:
    #         prompt (str): The prompt to send to the API
            
    #     Returns:
    #         str: The response from the API
    #     """
    #     try:
    #         url = "http://localhost:11434/api/generate"
    #         payload = {
    #             "model": self.config["model"],
    #             "prompt": prompt,
    #             "temperature": self.config["temperature"],
    #             "max_tokens": self.config["max_tokens"]
    #         }
            
    #         response = requests.post(url, json=payload)
    #         response.raise_for_status()
            
    #         # Ollama returns responses as JSON objects with streaming, 
    #         # we need to extract the full response
    #         full_response = ""
    #         for line in response.text.splitlines():
    #             if not line.strip():
    #                 continue
    #             try:
    #                 resp_json = json.loads(line)
    #                 if "response" in resp_json:
    #                     full_response += resp_json["response"]
    #             except json.JSONDecodeError:
    #                 continue
                    
    #         return full_response.strip()
        
    #     except Exception as e:
    #         logger.error(f"Error making Ollama API request: {str(e)}")
    #         return f"Error generating content: {str(e)}"
    
    def _openai_request(self, prompt: str) -> str:
        """
        Make a request to the OpenAI API.
        
        Args:
            prompt (str): The prompt to send to the API
            
        Returns:
            str: The response from the API
        """
        try:
            # Configure OpenAI client with API key
            client = openai.OpenAI(api_key=self.config["api_key"])
            
            # Create chat completion
            response = client.chat.completions.create(
                model=self.config["model"],
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that specializes in creating marketing content for products."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 150),
                top_p=self.config.get("top_p", 1.0),
                frequency_penalty=self.config.get("frequency_penalty", 0.0),
                presence_penalty=self.config.get("presence_penalty", 0.0)
            )
            
            # Extract the generated text from the response
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error making OpenAI API request: {str(e)}")
            return f"Error generating content: {str(e)}"
            
    # def _huggingface_request(self, prompt: str) -> str:
    #     """
    #     Make a request to the HuggingFace API.
        
    #     Args:
    #         prompt (str): The prompt to send to the API
            
    #     Returns:
    #         str: The response from the API
    #     """
    #     try:
    #         API_URL = f"https://api-inference.huggingface.co/models/{self.config['model']}"
    #         headers = {"Authorization": f"Bearer {self.config['api_key']}"}
            
    #         payload = {
    #             "inputs": prompt,
    #             "parameters": {
    #                 "max_length": self.config.get("max_tokens", 150),
    #                 "temperature": self.config.get("temperature", 0.7),
    #                 "top_p": self.config.get("top_p", 1.0),
    #                 "num_return_sequences": 1
    #             }
    #         }
            
    #         response = requests.post(API_URL, headers=headers, json=payload)
    #         response.raise_for_status()
            
    #         result = response.json()
    #         if isinstance(result, list) and len(result) > 0:
    #             return result[0].get("generated_text", "").strip()
    #         return result.get("generated_text", "").strip()
            
    #     except Exception as e:
    #         logger.error(f"Error making HuggingFace API request: {str(e)}")
    #         return f"Error generating content: {str(e)}"

    def generate_summary(self, description: str, features: List[str]) -> str:
        """
        Generate a concise 2-3 sentence summary for a product.
        
        Args:
            description (str): Product description
            features (List[str]): List of product features
            
        Returns:
            str: Generated summary
        """
        features_text = "\n".join([f"- {feature}" for feature in features])
        
        # Use the custom prompt from Implementation.txt
        prompt = (
            "You are an experienced Marketing specialist. Your task is to maximize sales for the product. "
            f"Please generate concise 2–3 sentence summary using the following information: "
            f"Product description {description}, key features {features_text}."
        )
        
        logger.info("Generating product summary")
        
        if self.provider == "OpenAI":
            return self._openai_request(prompt)

    def generate_tagline_and_highlights(self, description: str, features: List[str]) -> Dict[str, Any]:
        """
        Generate a tagline and bullet-point highlights for a product.
        
        Args:
            description (str): Product description
            features (List[str]): List of product features
            
        Returns:
            Dict[str, Any]: Dictionary containing tagline and highlights
        """
        features_text = "\n".join([f"- {feature}" for feature in features])
        
        # Use the custom prompt from Implementation.txt
        prompt = (
            "You are a marketing copywriter. Based on the following product description and key features, generate:\n"
            "1. A catchy, concise tagline (no more than 10 words) that communicates the product's main benefit.\n"
            "2. Five bullet-point highlights that summarize the most compelling features and advantages in a way "
            "that would appeal to customers.\n"
            f"Product Description: {description}\n"
            f"Key Features: {features_text}"
        )
        
        logger.info("Generating product tagline and highlights")
        
        if self.provider == "OpenAI":
            response = self._openai_request(prompt)
        
        # Parse the response to extract tagline and highlights
        try:
            lines = response.strip().split('\n')
            tagline = ""
            highlights = []
            
            # Extract tagline and highlights from the response
            in_tagline = False
            in_highlights = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check for tagline indicator
                if "tagline" in line.lower() or line.startswith('1.'):
                    in_tagline = True
                    in_highlights = False
                    # Extract if tagline is in the same line
                    if ':' in line:
                        tagline = line.split(':', 1)[1].strip().strip('"\'')
                    continue
                
                # Check for highlights indicator
                if "highlights" in line.lower() or "bullet" in line.lower() or line.startswith('2.'):
                    in_tagline = False
                    in_highlights = True
                    continue
                
                # Collect tagline
                if in_tagline and not in_highlights and not tagline:
                    tagline = line.strip('"\'')
                    in_tagline = False
                
                # Collect highlights
                if in_highlights and (line.startswith('-') or line.startswith('•') or 
                                    any(f"{i}." in line for i in range(1, 6))):
                    # Remove bullet points and numbering
                    highlight = line
                    for prefix in ['-', '•', '1.', '2.', '3.', '4.', '5.']:
                        if highlight.startswith(prefix):
                            highlight = highlight[len(prefix):].strip()
                            break
                    highlights.append(highlight)
            
            # If parsing logic fails, return raw response with defaults
            if not tagline or len(highlights) == 0:
                return {
                    "tagline": response.split('\n', 1)[0] if '\n' in response else response[:50],
                    "highlights": [response] if not '\n' in response else response.split('\n')[:5]
                }
                
            return {
                "tagline": tagline,
                "highlights": highlights[:5]  # Limit to 5 highlights
            }
                
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            # Return raw response if parsing fails
            return {
                "tagline": response.split('\n', 1)[0] if '\n' in response else response[:50],
                "highlights": [response] if not '\n' in response else response.split('\n')[:5]
            }

    def process_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single product through the LLM pipeline.
        
        Args:
            product (Dict[str, Any]): Product data dictionary
            
        Returns:
            Dict[str, Any]: Processed product with LLM-generated content
        """
        # Create a copy of the product to avoid modifying the original
        processed_product = product.copy()
        
        try:
            # Generate summary
            processed_product["summary"] = self.generate_summary(
                product.get("description", ""), 
                product.get("features", [])
            )
            
            # Generate tagline and highlights
            tagline_data = self.generate_tagline_and_highlights(
                product.get("description", ""), 
                product.get("features", [])
            )
            
            processed_product["tagline"] = tagline_data.get("tagline", "")
            processed_product["highlights"] = tagline_data.get("highlights", [])
            
            logger.info(f"Successfully processed product: {product.get('id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error processing product {product.get('id', 'unknown')}: {str(e)}")
            processed_product["summary"] = "Error generating summary"
            processed_product["tagline"] = "Error generating tagline"
            processed_product["highlights"] = ["Error generating highlights"]
            
        return processed_product

def process_all_products(input_path: Optional[str] = None, 
                        output_path: Optional[str] = None,
                        llm_provider: str = "OpenAI") -> List[Dict[str, Any]]:
    """
    Process all products in the input file through the LLM pipeline.
    
    Args:
        input_path (Optional[str]): Path to the input JSON file
        output_path (Optional[str]): Path to save the processed products
        llm_provider (str): LLM provider to use
        
    Returns:
        List[Dict[str, Any]]: List of processed products
    """
    # Use default paths if not provided
    input_path = input_path or DATA_PATHS["scraped_data"]
    output_path = output_path or DATA_PATHS["processed_data"]
    
    logger.info(f"Processing products from {input_path}")
    
    try:
        # Load products from the input file
        with open(input_path, 'r') as f:
            products = json.load(f)
        
        # Initialize the LLM processor
        processor = LLMProcessor(llm_provider=llm_provider)
        
        # Process each product
        processed_products = []
        for product in products:
            processed_product = processor.process_product(product)
            processed_products.append(processed_product)
            
        # Save the processed products
        with open(output_path, 'w') as f:
            json.dump(processed_products, f, indent=2)
            
        logger.info(f"Successfully processed {len(processed_products)} products")
        logger.info(f"Saved processed products to {output_path}")
        
        return processed_products
        
    except Exception as e:
        logger.error(f"Error processing products: {str(e)}")
        return []
        
if __name__ == "__main__":
    # Process all products with default settings
    process_all_products()
