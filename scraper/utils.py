"""
Utility functions for the Best Buy scraper.

This module contains reusable functions for scraping Best Buy product data.
"""
import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
# from pathlib import Path
from typing import Dict, List, Optional, Any

from playwright.async_api import Page
# from playwright.async_api import expect

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SCRAPER_CONFIG, DATA_PATHS, LOGGING_CONFIG


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Set up and configure the logger for the scraper.
    
    Args:
        name: Logger name (default: module name)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
    
    # Create formatter
    formatter = logging.Formatter(LOGGING_CONFIG["format"])
    
    # Create console handler and set level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
    console_handler.setFormatter(formatter)
    
    # Create file handler and set level
    log_file = LOGGING_CONFIG.get("file")
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)
        
        # Add timestamp to log filename to create unique logs for each run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"scraper_{timestamp}.log"
        log_path = os.path.join(log_dir, log_filename)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_path}")
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Prevent logs from being propagated to the root logger
    logger.propagate = False
    
    return logger


async def extract_product_urls(page: Page, logger: logging.Logger, source: str) -> List[str]:
    """
    Extract product URLs from a category page.
    
    Args:
        page: Playwright page object
        logger: Logger instance
        source: Source identifier (e.g., "BestBuy")
        
    Returns:
        List of product URLs
    """
    logger.info("Extracting product links")
    product_links = []
    
    # Define selectors for product items
    product_selectors = [
        ".x-productListItem",
        "div[class*='productLine']",
        "div[class*='product-item']",
        ".product-listing"
    ]
    
    # Try different selectors for product items
    for selector in product_selectors:
        product_elements = await page.query_selector_all(selector)
        if product_elements and len(product_elements) > 0:
            logger.info(f"Found {len(product_elements)} product elements with selector: {selector}")
            
            # Extract links from each product element
            for element in product_elements:
                try:
                    # Try to find the product link
                    link_selectors = [
                        "a[href*='/en-ca/product/']",
                        "a[data-automation='product-item-link']",
                        "a[class*='link']"
                    ]
                    
                    for link_selector in link_selectors:
                        link_element = await element.query_selector(link_selector)
                        if link_element:
                            href = await link_element.get_attribute("href")
                            if href and "/en-ca/product/" in href:
                                # Ensure we have a full URL
                                if href.startswith("http"):
                                    product_links.append(href)
                                else:
                                    product_links.append(f"{SCRAPER_CONFIG[source]['base_url']}{href}")
                            break
                except Exception as e:
                    logger.warning(f"Error extracting link: {e}")
            
            # If we found links, no need to try other selectors
            if product_links:
                break
    
    # Remove duplicates
    product_links = list(set(product_links))
    logger.info(f"Found {len(product_links)} unique product links")
    
    return product_links


async def extract_product_id(url: str, logger: logging.Logger) -> str:
    """
    Extract product ID from URL.
    
    Args:
        url: Product URL
        logger: Logger instance
        
    Returns:
        Product ID
    """
    # Try to extract product ID from URL
    try:
        # URLs typically end with a product ID like /product-name/12345678
        product_id = url.split("/")[-1]
        
        # Check if it's a numeric ID
        if product_id.isdigit():
            return product_id
        
        # If not, try to extract from the URL path
        parts = url.split("/")
        for part in reversed(parts):
            if part.isdigit():
                return part
    except Exception:
        pass
    
    # If extraction fails, generate an ID from the URL
    logger.debug(f"Could not extract numeric ID from URL, generating hash: {url}")
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:10]


async def extract_title(page: Page, logger: logging.Logger) -> Optional[str]:
    """
    Extract product title from the product page.
    
    Args:
        page: Playwright page object
        logger: Logger instance
        
    Returns:
        Product title or None if not found
    """
    # Title extraction
    title = ""
    title_selectors = [
        "h1[data-automation='product-title']",
        "h1.productName_2KoPa",
        "h1[class*='title']",
        "h1[itemprop='name']"
    ]
    
    for selector in title_selectors:
        try:
            title_element = await page.query_selector(selector)
            if title_element:
                title = await title_element.inner_text()
                if title:
                    logger.debug(f"Extracted title: {title} using selector: {selector}")
                    break
        except Exception as e:
            logger.debug(f"Error with title selector {selector}: {e}")
    
    if not title:
        logger.warning("Could not find title for product")
        return None
        
    return title


async def extract_price(page: Page, logger: logging.Logger, title: str) -> str:
    """    
    Args:
        page: Playwright page object
        product_id: Product ID extracted from URL
        url: Full URL of the product
        
    Returns:
        str: Extracted price 
    """
    
    # JSON-LD data
    try:
        script_content = await page.evaluate('''
            Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
                .map(script => script.textContent)
        ''')
        
        for content in script_content:
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    # Check for price in offers
                    if 'offers' in data and isinstance(data['offers'], dict) and 'price' in data['offers']:
                        price = f"${data['offers']['price']}"
                        logger.info(f"Found price in JSON-LD offers: {price}")
                        break
                    # Check for price directly in data
                    elif 'price' in data:
                        price = f"${data['price']}"
                        logger.info(f"Found price in JSON-LD root: {price}")
                        break
            except Exception:
                continue
    except Exception as e:
        print(f"Error extracting from JSON-LD: {str(e)}")
    
    return price.strip() if price else "Price not found"


async def extract_description(page: Page, logger: logging.Logger) -> str:
    """
    Extract product description from the product page.
    
    Args:
        page: Playwright page object
        logger: Logger instance
        
    Returns:
        Product description or empty string if not found
    """
    description = ""
    
    # First try the product overview tab
    overview_tab_selectors = [
        "button[data-automation='overview-tab']", 
        "button:has-text('Overview')",
        "#overview"
    ]
    
    for selector in overview_tab_selectors:
        try:
            overview_tab = await page.query_selector(selector)
            if overview_tab:
                await overview_tab.click()
                await page.wait_for_timeout(1000)  # Wait for content to load
                break
        except Exception:
            continue
    
    # Try different selectors for description content
    description_selectors = [
        "div[data-automation='overview-content']",
        "div[class*='overview']",
        "div[class*='description']",
        "div[itemprop='description']"
    ]
    
    for selector in description_selectors:
        try:
            description_element = await page.query_selector(selector)
            if description_element:
                text = await description_element.inner_text()
                if text and len(text) > 100:  # Ensure it's substantial enough to be a description
                    description = text
                    logger.info(f"Found description with selector: {selector}")
                    logger.info(f"Description length: {len(description)} characters")
                    break
        except Exception:
            continue
    
    # If couldn't find the description in structured elements, try generic divs
    if not description:
        # Get all divs with substantial text
        try:
            divs = await page.query_selector_all("div")
            for div in divs:
                text = await div.inner_text()
                if text:
                    # Look for divs with a decent amount of text that might be a description
                    if len(text) > 100 and len(text) < 2000:
                        # Check if it has keywords that suggest it's a product description
                        text_lower = text.lower()
                        if any(keyword in text_lower for keyword in ["features", "designed", "watch", "track", "monitor", "battery", "display"]):
                            description = text
                            logger.info("Found description in generic div with product-related content")
                            logger.info(f"Description length: {len(description)} characters")
                            break
        except Exception:
            pass
    
    # Truncate very long descriptions
    if len(description) > 1000:
        description = description[:1000] + "..."
    
    if not description:
        logger.warning("No product description found")
        
    return description


async def extract_rating(page: Page, logger: logging.Logger, title: str) -> str:
    """
    Extract product rating from the product page using Playwright locators.
    Attempts to find and click a reviews button to access detailed rating information.
    
    Args:
        page: Playwright page object
        logger: Logger instance
        title: Product title for logging context
        
    Returns:
        Product rating or "Not rated" if not found
    """
    rating = "Not rated"
    logger.info(f"Starting rating extraction for product: {title}")
    
    # Try Approach 1: Click the reviews button to reveal rating information
    clicked = False
    try:
        # Find the Customer Reviews button
        review_button = page.locator("button, a").filter(has_text="Customer Reviews").first
        is_visible = await review_button.is_visible()
        
        if is_visible:
            logger.info("Found visible Customer Reviews button")
            
            # Save current URL to check if we navigate away
            current_url = page.url
            
            # Click the button
            await review_button.click()
            clicked = True
            logger.info("Clicked Customer Reviews button")
            
            # Wait for any content to load
            await page.wait_for_timeout(500)
            
            # If URL changed, we might have navigated to a reviews page
            if page.url != current_url:
                logger.info(f"Navigated to reviews page: {page.url}")
    except Exception as e:
        logger.info(f"No reviews button found or could not click: {e}")
        clicked = False
    
    # After clicking, look for rating information in any newly displayed content
    if clicked:
        try:
            # Wait a moment for any dynamic content to load
            await page.wait_for_timeout(500)
            
            # Look for the rating directly - optimized approach
            # First try the most common rating element
            rating_element = page.locator("[class*='rating'], [class*='reviews'] span:first-child").first
            rating_text = await rating_element.text_content()
            
            logger.info(f"Found rating text: '{rating_text}'")
            
            # Extract numeric rating
            import re
            rating_match = re.search(r'([0-9]+\.?[0-9]*)', rating_text)
            if rating_match:
                rating = rating_match.group(1)
                logger.info(f"✅ Extracted rating: {rating}")
                return rating
        except Exception as e:
            logger.info(f"Could not extract rating after clicking: {e}")
    
    # Try Approach 2: Simple fallback - look for rating information directly on the page
    if rating == "Not rated":
        try:
            # Use a direct locator approach instead of looping through selectors
            rating_locator = page.locator("[class*='rating'], [class*='reviews'] span:first-child, span[data-automation='reviewsStarRating']").first
            rating_text = await rating_locator.text_content()
            
            # Try to extract numeric rating with regex
            import re
            rating_match = re.search(r'([0-9]+\.?[0-9]*)', rating_text)
            if rating_match:
                rating = rating_match.group(1)
                logger.info(f"Found direct rating: {rating}")
            
                # Validate the rating
                if rating.replace('.', '', 1).isdigit():
                    logger.info(f"✓ Rating validation passed: '{rating}' is numeric")
                else:
                    logger.warning(f"⚠️ Rating validation warning: '{rating}' doesn't look like a valid rating")
        except Exception as e:
            # Silently catch errors
            logger.debug(f"Fallback rating extraction failed: {e}")
    
    # Log final result
    if rating == "Not rated":
        logger.info(f"❌ No rating found for product: {title}")
    else:
        logger.info(f"✅ Successfully extracted final rating: '{rating}'")
    
    return rating


async def extract_features(page: Page, logger: logging.Logger, title: str) -> List[str]:
    """
    Extract product features from the "About this product" section.
    
    Args:
        page: Playwright page object
        logger: Logger instance
        title: Product title for logging context
        
    Returns:
        List of product features or empty list if none found
    """
    features_list = []
    logger.info(f"Starting features extraction for: {title}")
    
    try:
        # Find the "About this product" section which may already be visible
        about_section = page.locator("[class*='about-product'], [class*='about-this-product'], [class*='overview']").first
        
        # If not immediately visible, try to find and click the button
        if not await about_section.is_visible():
            logger.info("About section not immediately visible, looking for button")
            about_button = page.locator("button, a").filter(has_text="About this product").first
            
            if await about_button.is_visible():
                logger.info("Found 'About this product' button")
                try:
                    await about_button.click()
                    logger.info("Clicked 'About this product' button")
                    await page.wait_for_timeout(1000)  # Wait for content to load
                except Exception as click_err:
                    logger.info(f"Could not click button: {click_err}")
        
        # Now try to extract the content
        # First look for bullet points which are common in the About section
        bullet_points = page.locator("[class*='overview'] li, [class*='about'] li, [class*='features'] li")
        bullet_count = await bullet_points.count()
        
        if bullet_count > 0:
            logger.info(f"Found {bullet_count} bullet points in About section")
            features = []
            
            for i in range(bullet_count):
                point = await bullet_points.nth(i).text_content()
                if point and point.strip():
                    features.append(point.strip())
            
            if features:
                features_list = features  # Directly assign the features list
                logger.info(f"Extracted {len(features_list)} features")
                
    except Exception as e:
        logger.info(f"Error extracting product features: {e}")
    
    if not features_list:
        logger.info(f"No features found for: {title}")
    else:
        logger.info(f"✅ Successfully extracted {len(features_list)} features")
    
    return features_list

    
def save_data(products: List[Dict], output_path: str, logger: logging.Logger) -> None:
    """
    Save product data to a JSON file.
    
    Args:
        products: List of product dictionaries
        output_path: Path to save the JSON file
        logger: Logger instance
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    logger.info(f"Saving {len(products)} products to {output_path}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Data saved to {output_path}")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Scrape products from Best Buy")
    parser.add_argument("--count", type=int, default=10, help="Number of products to scrape")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--visible", action="store_false", dest="headless", help="Run browser in visible mode")
    parser.add_argument("--source", type=str, default="BestBuy", help="Source name to include in product data")
    parser.add_argument("--category", type=str, default="Laptops", help="Category to scrape (default: Laptops)")
    
    return parser.parse_args()


async def scrape_single_product(page: Page, url: str, source: str, logger: logging.Logger, category: str) -> Optional[Dict[str, Any]]:
    """
    Scrape details for a single product.
    
    Args:
        page: Playwright page object
        url: Product URL
        source: Source identifier (e.g., "BestBuy")
        logger: Logger instance
        category: Category to include in product data
        
    Returns:
        Product data dictionary or None if scraping failed
    """
    logger.info(f"Scraping product: {url}")
    
    try:
        # Navigate to the product page
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(1000)  # Allow time for page to fully load
        
        # Extract product details
        title = await extract_title(page, logger)
        if not title:
            logger.warning(f"Could not find title for {url}")
            return None
            
        price = await extract_price(page, logger, title)
        description = await extract_description(page, logger)
        rating = await extract_rating(page, logger, title)
        features = await extract_features(page, logger, title)
        product_id = await extract_product_id(url, logger)
        
        # Create product data dictionary
        product_data = {
            "id": f"{SCRAPER_CONFIG[source]['base_url'].split('://')[1].split('.')[0]}-{product_id}",
            "category": category,
            "title": title,
            "price": price,
            "description": description,
            "features": features,
            "url": url,
            "rating": rating,
            "source": source,
            "scraped_at": datetime.now().isoformat(),
        }
        
        logger.info(f"Successfully scraped product: {title}")
        return product_data
        
    except Exception as e:
        logger.error(f"Error scraping product {url}: {e}")
        return None


if __name__ == "__main__":
    # This allows the module to be imported without running the main code
    # while still providing a way to run it directly
    pass
