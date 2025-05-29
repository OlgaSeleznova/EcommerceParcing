"""
Smartwatch Scraper for Best Buy Canada

This script is specifically optimized to scrape smartwatch products from Best Buy Canada.
It addresses the specific structure of the smartwatch category page.
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
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
)
logger = logging.getLogger(__name__)

# Ensure the data directory exists
Path(os.path.dirname(DATA_PATHS["scraped_data"])).mkdir(parents=True, exist_ok=True)

async def scrape_smartwatches(count: int = 10, headless: bool = True) -> List[Dict]:
    """
    Scrape smartwatch products from Best Buy Canada.
    
    Args:
        count: Number of products to scrape
        headless: Whether to run the browser in headless mode
        
    Returns:
        A list of dictionaries containing product data
    """
    logger.info(f"Starting Best Buy smartwatch scraper")
    products = []
    
    # Get the smartwatch category URL
    category_url = SCRAPER_CONFIG["BESTBUY"]["categories"]["smartwatches"]["url"]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=SCRAPER_CONFIG["BESTBUY"]["user_agent"],
            viewport={"width": 1920, "height": 1080},
        )
        
        # Add headers to all requests
        await context.set_extra_http_headers(SCRAPER_CONFIG["BESTBUY"]["headers"])
        
        # Create a new page
        page = await context.new_page()
        
        try:
            # Navigate to the smartwatch category page
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
                                            product_links.append(f"{SCRAPER_CONFIG['BESTBUY']['base_url']}{href}")
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
            
            # 2. Price
            price = ""
            price_selectors = [
                "span[data-automation='product-price']",
                ".price_FHDfG",
                ".large-price_3CcV5"
            ]
            for selector in price_selectors:
                price_element = await page.query_selector(selector)
                if price_element:
                    price_text = await price_element.inner_text()
                    if price_text:
                        # Clean up price (remove $ and commas)
                        import re
                        price_match = re.search(r'\\$?(\\d[\\d,.]*)', price_text)
                        if price_match:
                            price = price_match.group(1).replace(",", "").replace("$", "")
                        else:
                            price = price_text.replace("$", "").replace(",", "")
                        break
            
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
                            if any(keyword in text_lower for keyword in ["features", "designed", "smartwatch", "watch", "track", "monitor", "battery", "display"]):
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
            
            # 4. Specifications
            specs = {}
            
            # Try to click on specifications tab if it exists
            spec_tab_selectors = [
                "button[data-automation='specifications-tab']",
                "button:has-text('Specifications')",
                "button:has-text('Specs')"
            ]
            
            for selector in spec_tab_selectors:
                try:
                    spec_tab = await page.query_selector(selector)
                    if spec_tab:
                        await spec_tab.click()
                        await page.wait_for_timeout(1000)  # Wait for specs to load
                        break
                except Exception:
                    continue
            
            # Look for specifications in table format
            spec_table_selectors = [
                "table.specifications",
                "div[data-automation='specifications-content'] table"
            ]
            
            for table_selector in spec_table_selectors:
                spec_rows = await page.query_selector_all(f"{table_selector} tr")
                if spec_rows and len(spec_rows) > 0:
                    for row in spec_rows:
                        try:
                            name_elem = await row.query_selector("td:first-child, th:first-child")
                            value_elem = await row.query_selector("td:nth-child(2), th:nth-child(2)")
                            
                            if name_elem and value_elem:
                                name = await name_elem.inner_text()
                                value = await value_elem.inner_text()
                                if name.strip() and value.strip():
                                    specs[name.strip()] = value.strip()
                        except Exception:
                            continue
            
            # 5. Rating
            rating = "Not rated"
            rating_selectors = [
                "span[data-automation='reviewsStarRating']",
                ".rating_2WbU5"
            ]
            for selector in rating_selectors:
                rating_element = await page.query_selector(selector)
                if rating_element:
                    rating_text = await rating_element.inner_text()
                    if rating_text:
                        import re
                        rating_match = re.search(r'([\\d\\.]+)', rating_text)
                        if rating_match:
                            rating = rating_match.group(1)
                        else:
                            rating = rating_text
                        break
            
            # 6. Image URL
            image_url = ""
            image_selectors = [
                "img[data-automation='image-gallery-main-image']",
                ".productGallery_1jeLb img",
                ".gallery_1nJpr img"
            ]
            
            for selector in image_selectors:
                image_element = await page.query_selector(selector)
                if image_element:
                    src = await image_element.get_attribute("src")
                    if src:
                        image_url = src
                        break
            
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
            
            # Create product data dictionary
            product_data = {
                "id": f"bb-{product_id}",
                "title": title,
                "price": price,
                "description": description,
                "specifications": specs,
                "url": url,
                "rating": rating,
                "image_url": image_url,
                "source": "Best Buy",
                "category": "Smartwatches",
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
    parser = argparse.ArgumentParser(description="Scrape smartwatches from Best Buy Canada")
    parser.add_argument("--count", type=int, default=10, help="Number of products to scrape")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--visible", action="store_false", dest="headless", help="Run browser in visible mode")
    
    args = parser.parse_args()
    
    products = await scrape_smartwatches(count=args.count, headless=args.headless)
    
    if products:
        print(f"\nSuccessfully scraped {len(products)} smartwatches from Best Buy Canada.")
        print(f"Data saved to {DATA_PATHS['scraped_data']}")
    else:
        print("No products were scraped. Check the logs for details.")

if __name__ == "__main__":
    asyncio.run(main())
