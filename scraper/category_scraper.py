"""
Scraper for Best Buy

This script is specifically optimized to scrape products from Best Buy
It addresses the specific structure of the category page.
"""
import argparse
import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import async_playwright
from tqdm import tqdm

# Add the parent directory to the path so we can import from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SCRAPER_CONFIG, DATA_PATHS, LOGGING_CONFIG

# Set up logging
logger = logging.getLogger(__name__)
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

# Ensure the data directory exists
Path(os.path.dirname(DATA_PATHS["scraped_data"])).mkdir(parents=True, exist_ok=True)

async def scrape_products(count: int = 10, headless: bool = True, source: str = "BestBuy") -> List[Dict]:
    """
    Scrape products from Best Buy
    
    Args:
        count: Number of products to scrape
        headless: Whether to run the browser in headless mode
        source: Source name to include in product data (default: Best Buy)
        
    Returns:
        A list of dictionaries containing product data
    """
    logger.info(f"Starting scraper")
    products = []
    
    # Get the category URL
    category_url = SCRAPER_CONFIG[source]["categories"][0]["url"]
    
    # Store source as a function attribute to pass it to scrape_product_details
    scrape_product_details.source = source
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=SCRAPER_CONFIG[source]["user_agent"],
            viewport={"width": 1920, "height": 1080},
        )
        
        # Add headers to all requests
        await context.set_extra_http_headers(SCRAPER_CONFIG[source]["headers"])
        
        # Create a new page
        page = await context.new_page()
        
        try:
            # Navigate to the category page
            logger.info(f"Navigating to: {category_url}")
            await page.goto(category_url, timeout=60000)
            
            # Wait for products to load - try several selectors
            product_selectors = [
                ".x-productListItem",
                ".productItemContainer_E8SSw",
                "div[data-automation='product-list-item']"
            ]
            
            # Wait for any of the product selectors to appear
            for selector in product_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    logger.info(f"Found products with selector: {selector}")
                    break
                except Exception:
                    continue
            
            # Scroll down to load more products
            logger.info("Scrolling to load more products")
            for _ in range(5):  # Scroll multiple times to ensure we load enough products
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)  # Wait for content to load
            
            # Extract product links
            logger.info("Extracting product links")
            product_links = []
            
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
            
            # Remove duplicates and limit to the number requested
            product_links = list(set(product_links))
            logger.info(f"Found {len(product_links)} unique product links")
            
            if not product_links:
                logger.error("No product links found. Taking screenshot for debugging.")
                await page.screenshot(path="debug_no_products.png")
                return []
            
            # Scrape details for each product
            for i, url in enumerate(tqdm(product_links[:count], desc="Scraping products")):
                if i > 0:
                    # Add delay between requests to avoid rate limiting
                    await asyncio.sleep(random.uniform(1, 3))
                
                try:
                    product_data = await scrape_product_details(page, url)
                    if product_data:
                        products.append(product_data)
                        logger.info(f"Successfully scraped product: {product_data.get('title', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Error scraping product {url}: {e}")
            
            logger.info(f"Successfully scraped {len(products)} products")
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            # Take a screenshot for debugging
            await page.screenshot(path="error_screenshot.png")
            logger.info("Saved error screenshot to error_screenshot.png")
        finally:
            await browser.close()
    
    # Save the scraped data
    if products:
        save_data(products)
    
    return products

async def scrape_product_details(page, url: str) -> Optional[Dict]:
    """
    Scrape details for a single product.
    
    Args:
        page: The Playwright page object
        url: The URL of the product page
        
    Returns:
        A dictionary containing product details or None if scraping failed
    """
    logger.info(f"Scraping product: {url}")
    
    for attempt in range(3):  # Try up to 3 times
        try:
            # Navigate to the product page
            await page.goto(url, timeout=45000)
            
            # Wait for the product page to load
            await page.wait_for_selector("h1", timeout=10000)
            
            # Extract product details
            
            # 1. Title
            title = ""
            title_selectors = [
                "h1[data-automation='product-title']",
                "h1.title_3a6Uh",
                "h1"
            ]
            for selector in title_selectors:
                title_element = await page.query_selector(selector)
                if title_element:
                    title = await title_element.inner_text()
                    if title:
                        break
            
            if not title:
                logger.warning(f"Could not find title for {url}")
                continue
            
            # # 2. Price
            # price = ""
            # price_selectors = [
            #     "span[data-automation='product-price']",
            #     ".price_FHDfG",
            #     ".large-price_3CcV5",
            #     "span[data-automation='product-price'] div[class*='price']"
            # ]
            # for selector in price_selectors:
            #     price_element = await page.query_selector(selector)
            #     if price_element:
            #         price_text = await price_element.inner_text()
            #         if price_text:
            #             # Simple direct cleaning of the price text
            #             price = price_text.strip()
            #             # Remove currency symbols and formatting characters
            #             # price = price.replace("$", "").replace("CAD", "").replace(",", "").strip()
            #             logger.info(f"Extracted price: {price} from text: {price_text}")
            #             break

            # 2. Price
            price = ""
            logger.info(f"Starting price extraction for product: {title}")
            price_selectors = [
                "span[data-automation='product-price']",
                ".price_FHDfG",
                ".large-price_3CcV5",
                "span[data-automation='product-price'] div[class*='price']",
                ".pricingContainer_Po8VO span",
                ".priceContainer_1BHcQ span",
                ".pricing_LfYWF span"
            ]
            
            # Log all selectors we're trying
            logger.debug(f"Price selectors to try: {', '.join(price_selectors)}")
            
            for selector in price_selectors:
                try:
                    logger.debug(f"Trying price selector: {selector}")
                    price_element = await page.query_selector(selector)
                    if price_element:
                        price_text = await price_element.inner_text()
                        logger.debug(f"Found element with selector {selector}, text content: '{price_text}'")
                        
                        if price_text:
                            # Simple direct cleaning of the price text
                            price = price_text.strip()
                            logger.info(f"Extracted price: '{price}' from text: '{price_text}' using selector: {selector}")
                            
                            # Check if the price looks valid (contains $ or digits)
                            if '$' in price or any(c.isdigit() for c in price):
                                logger.info(f"✓ Price validation passed: '{price}' contains expected characters")
                            else:
                                logger.warning(f"⚠️ Price validation warning: '{price}' doesn't look like a valid price")
                                
                            # Add DOM context for debugging
                            try:
                                parent_html = await page.evaluate("(el) => el.parentElement.outerHTML", price_element)
                                logger.debug(f"Price element parent HTML: {parent_html[:200]}...")
                            except Exception as e:
                                logger.debug(f"Could not get parent HTML: {e}")
                                
                            break
                        else:
                            logger.debug(f"Empty text content from price selector: {selector}")
                except Exception as e:
                    logger.debug(f"Error with price selector {selector}: {e}")
                    continue
                    
            if not price:
                logger.warning(f"❌ Failed to extract price for product: {title}")
            else:
                logger.info(f"✅ Successfully extracted final price: '{price}'")
            
            # 3. Description (Overview)
            description = ""
            
            # First try the product overview tab
            overview_tab_selectors = [
                "button[data-automation='overview-tab']", 
                "button:has-text('Overview')",
                ".tab-overview"
            ]
            
            for selector in overview_tab_selectors:
                try:
                    overview_tab = await page.query_selector(selector)
                    if overview_tab:
                        await overview_tab.click()
                        await page.wait_for_timeout(1000)  # Wait for overview content to load
                        break
                except Exception:
                    continue
            
            # Try different description selectors with more options
            desc_selectors = [
                "div[data-automation='productDescription']",
                "div[data-automation='overview-content']",
                "div[data-automation='product-overview']",
                ".description_1GJqI",
                ".descriptionContainer_2PLkv",
                ".tab-content-overview",
                ".overview_3fZXP",
                ".overview-tab-content",
                ".product-description",
                ".prod-desc",
                ".product-overview"
            ]
            
            for selector in desc_selectors:
                desc_element = await page.query_selector(selector)
                if desc_element:
                    description = await desc_element.inner_text()
                    if description:
                        logger.info(f"Found description with selector: {selector}")
                        break
            
            # If still no description, try to find any div with a significant amount of text
            if not description:
                try:
                    # Get all divs on the page
                    divs = await page.query_selector_all("div")
                    for div in divs:
                        text = await div.inner_text()
                        # Only consider text blocks with a reasonable length
                        if len(text) > 100 and len(text) < 2000:
                            # Check if it has keywords that suggest it's a product description
                            text_lower = text.lower()
                            if any(keyword in text_lower for keyword in ["features", "designed", "watch", "track", "monitor", "battery", "display"]):
                                description = text
                                logger.info("Found description in generic div with product-related content")
                                break
                except Exception as e:
                    logger.warning(f"Error in fallback description extraction: {e}")
                    
            # Last resort: use meta description
            if not description:
                try:
                    meta_desc = await page.evaluate("document.querySelector('meta[name=\"description\"]')?.getAttribute('content') || ''")
                    if meta_desc and len(meta_desc) > 20:  # Only use if somewhat substantial
                        description = meta_desc
                        logger.info("Using meta description as fallback")
                except Exception:
                    pass
            
            # Clean up description text
            if description:
                # Remove excessive whitespace
                description = " ".join(description.split())
                # Limit length to reasonable size
                if len(description) > 1000:
                    description = description[:997] + "..."
                    
            logger.info(f"Description length: {len(description)} characters")
            if not description:
                logger.warning("No product description found")
            
            
            # # 5. Rating
            # rating = "Not rated"
            # rating_selectors = [
            #     "span[data-automation='reviewsStarRating']",
            #     ".rating_2WbU5"
            # ]
            # for selector in rating_selectors:
            #     rating_element = await page.query_selector(selector)
            #     if rating_element:
            #         rating_text = await rating_element.inner_text()
            #         if rating_text:
            #             import re
            #             rating_match = re.search(r'([\\d\\.]+)', rating_text)
            #             if rating_match:
            #                 rating = rating_match.group(1)
            #             else:
            #                 rating = rating_text
            #             break

            # 5. Rating
            rating = "Not rated"
            logger.info(f"Starting rating extraction for product: {title}")
            rating_selectors = [
                "span[data-automation='reviewsStarRating']",
                ".rating_2WbU5",
                ".customerRating_28JCg span",
                "div[class*='rating'] span"
            ]
            
            # Log all selectors we're trying
            logger.debug(f"Rating selectors to try: {', '.join(rating_selectors)}")
            
            for selector in rating_selectors:
                try:
                    logger.debug(f"Trying rating selector: {selector}")
                    rating_element = await page.query_selector(selector)
                    if rating_element:
                        rating_text = await rating_element.inner_text()
                        logger.debug(f"Found element with selector {selector}, text content: '{rating_text}'")
                        
                        if rating_text:
                            # Try to extract numeric rating
                            import re
                            rating_match = re.search(r'([\\d\\.]+)', rating_text)
                            if rating_match:
                                rating = rating_match.group(1)
                                logger.info(f"Extracted numeric rating: '{rating}' from text: '{rating_text}'")
                            else:
                                rating = rating_text
                                logger.info(f"Using full rating text: '{rating}'")
                            
                            # Validate the rating format
                            if rating.replace('.', '', 1).isdigit():
                                logger.info(f"✓ Rating validation passed: '{rating}' is numeric")
                            else:
                                logger.warning(f"⚠️ Rating validation warning: '{rating}' doesn't look like a valid rating")
                            
                            break
                        else:
                            logger.debug(f"Empty text content from rating selector: {selector}")
                except Exception as e:
                    logger.debug(f"Error with rating selector {selector}: {e}")
                    continue
            
            if rating == "Not rated":
                logger.info(f"❌ No rating found for product: {title}")
            else:
                logger.info(f"✅ Successfully extracted final rating: '{rating}'")
            
            
            # Extract product ID from URL
            product_id = ""
            try:
                if "/product/" in url:
                    product_id = url.split("/product/")[1].split("/")[1]
                else:
                    import hashlib
                    product_id = hashlib.md5(url.encode()).hexdigest()[:10]
            except Exception:
                import hashlib
                product_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            # Get source from function parameter via closure first, before accessing config
            source = getattr(scrape_product_details, 'source', "BestBuy")
            
            # Find category slug from URL based on current config structure
            category_slug = "unknown"
            
            # Try to match the URL with category URLs in the config
            # The categories are now in a list instead of a dictionary
            for category in SCRAPER_CONFIG[source]["categories"]:
                category_url = category["url"]
                # Check if the category URL is part of the product URL or vice versa
                # Also extract the domain part for matching (e.g., bestbuy.ca/en-ca/category)
                domain_part = "/".join(category_url.split("/")[:5])  # Get domain and category part
                if domain_part in url or category["slug"] in url.lower():
                    category_slug = category["slug"]
                    logger.info(f"Detected category: {category_slug}")
                    break
            
            # Create product data dictionary using values from SCRAPER_CONFIG
            product_data = {
                "id": f"{SCRAPER_CONFIG[source]['base_url'].split('://')[1].split('.')[0]}-{product_id}",
                "title": title,
                "price": price,
                "description": description,
                "url": url,
                "rating": rating,
                "source": source,
                "category": category_slug,
                "scraped_at": datetime.now().isoformat(),
            }
            
            return product_data
            
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {url}: {str(e)}")
            if attempt < 2:  # Don't sleep after the last attempt
                await asyncio.sleep(random.uniform(2, 5))
    
    logger.error(f"Failed to scrape product after 3 attempts: {url}")
    return None

def save_data(products: List[Dict]) -> None:
    """
    Save the scraped data to a JSON file.
    
    Args:
        products: A list of dictionaries containing product data
    """
    if not products:
        logger.warning("No products to save")
        return
    
    output_file = DATA_PATHS["scraped_data"]
    logger.info(f"Saving {len(products)} products to {output_file}")
    
    with open(output_file, "w") as f:
        json.dump(products, f, indent=2)
    
    logger.info(f"Data saved to {output_file}")

async def main():
    """
    Main function to run the scraper.
    """
    parser = argparse.ArgumentParser(description="Scrape products from Best Buy")
    parser.add_argument("--count", type=int, default=10, help="Number of products to scrape")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--visible", action="store_false", dest="headless", help="Run browser in visible mode")
    parser.add_argument("--source", type=str, default="BestBuy", help="Source name to include in product data")
    
    args = parser.parse_args()
    
    products = await scrape_products(count=args.count, headless=args.headless, source=args.source)
    
    if products:
        print(f"\nSuccessfully scraped {len(products)} products from Best Buy")
        print(f"Data saved to {DATA_PATHS['scraped_data']}")
    else:
        print("No products were scraped. Check the logs for details.")

if __name__ == "__main__":
    asyncio.run(main())