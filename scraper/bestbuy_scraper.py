"""
Best Buy Scraper

This module contains the functionality to scrape product data from Best Buy's website.
It uses Playwright for browser automation to handle dynamic content loading.
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
from typing import Dict, List, Optional, Union

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

class BestBuyScraper:
    """
    A scraper class for extracting product data from Best Buy.
    
    This class uses Playwright to automate browser interactions and scrape
    product details from Best Buy's website.
    """
    
    def __init__(self, category: str, count: int = 10, headless: bool = True):
        """
        Initialize the Best Buy scraper.
        
        Args:
            category: The product category to scrape (e.g., 'computers_tablets', 'tv_home_theater')
            count: The number of products to scrape
            headless: Whether to run the browser in headless mode
        """
        self.config = SCRAPER_CONFIG["BESTBUY"]
        self.category = category
        self.count = count
        self.headless = headless
        self.products = []
        
        # Validate the category
        if category not in self.config["categories"]:
            valid_categories = ", ".join(self.config["categories"].keys())
            raise ValueError(
                f"Invalid category: '{category}'. "
                f"Valid categories are: {valid_categories}"
            )
    
    async def start(self) -> List[Dict]:
        """
        Start the scraping process.
        
        Returns:
            A list of dictionaries containing product data
        """
        logger.info(f"Starting Best Buy scraper for category: {self.category}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=self.config["user_agent"],
                viewport={"width": 1920, "height": 1080},
            )
            
            # Add headers to all requests
            await context.set_extra_http_headers(self.config["headers"])
            
            # Add stealth mode to avoid detection
            await context.add_init_script(path="scraper/stealth.min.js")
            
            page = await context.new_page()
            
            # Navigate to the category page - the Canadian site uses full URLs already
            category_url = self.config['categories'][self.category]['url']
            logger.info(f"Navigating to: {category_url}")
            
            try:
                # Navigate with a longer timeout and use domcontentloaded instead of networkidle
                await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for any selector that indicates products are loaded - Best Buy Canada selectors
                for selector in [".x-productListItem", ".productLine_2jZSU", ".productItemContainer_E8SSw", ".container_2aEKw", ".product-list div[class*='product']"]:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        logger.info(f"Found products with selector: {selector}")
                        break
                    except Exception:
                        continue
                
                # Extract products
                product_links = await self._extract_product_links(page)
                
                # Scrape product details
                for i, product_link in enumerate(tqdm(product_links[:self.count], desc="Scraping products")):
                    if i > 0:
                        # Add delay between requests to avoid rate limiting
                        await asyncio.sleep(self.config["request_delay"] + random.random())
                    
                    product_data = await self._scrape_product_details(page, product_link)
                    if product_data:
                        self.products.append(product_data)
                        logger.info(f"Successfully scraped product: {product_data['title']}")
                
                logger.info(f"Successfully scraped {len(self.products)} products")
                
            except Exception as e:
                logger.error(f"Error during scraping: {str(e)}")
            finally:
                await browser.close()
        
        # Save the scraped data
        self._save_data()
        
        return self.products
    
    async def _extract_product_links(self, page) -> List[str]:
        """
        Extract product links from the category page.
        
        Args:
            page: The Playwright page object
            
        Returns:
            A list of product URLs
        """
        logger.info("Extracting product links")
        
        # Try different selectors for product items - Best Buy Canada selectors
        product_item_selectors = [
            ".x-productListItem", 
            ".productLine_2jZSU", 
            ".productItemContainer_E8SSw",
            ".container_2aEKw",
            "div[data-automation='product-list-item']",
            ".product-list div[class*='product']"
        ]
        product_elements = []
        
        for selector in product_item_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    logger.info(f"Found {len(elements)} product elements with selector: {selector}")
                    product_elements = elements
                    break
            except Exception as e:
                logger.warning(f"Error finding product elements with selector {selector}: {str(e)}")
        
        if not product_elements:
            logger.warning("No product elements found with any of the selectors")
            # Take a screenshot for debugging
            await page.screenshot(path="scraper_debug.png")
            logger.info("Saved screenshot to scraper_debug.png for debugging")
            
            # Try a more general approach - find all links on the page
            logger.info("Attempting to find product links using a more general approach")
            return await self._extract_links_general_approach(page)
        
        # Scroll down to load more products if needed
        last_height = await page.evaluate("document.body.scrollHeight")
        max_scroll_attempts = 8
        scroll_attempts = 0
        
        while len(product_elements) < self.count * 2 and scroll_attempts < max_scroll_attempts:
            logger.info(f"Scrolling to load more products (attempt {scroll_attempts+1}/{max_scroll_attempts})")
            # Scroll down in smaller increments for smoother loading
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(1000)  # Wait for content to load
            
            new_height = await page.evaluate("document.body.scrollHeight")
            # Check if we reached bottom of page or height didn't change
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_height = new_height
            
            # Refresh the product elements count
            for selector in product_item_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        product_elements = elements
                        logger.info(f"Now found {len(product_elements)} product elements")
                        break
                except Exception:
                    continue
        
        # Extract product links - Best Buy Canada selectors
        product_links = []
        link_selectors = [
            "a[href*='/en-ca/product/']", 
            "a[data-automation='product-item-link']",
            "a[data-automation='product-image-link']",
            "a[class*='link']",
            "a[href]"
        ]  
        
        for element in product_elements:
            try:
                # Try different link selectors
                link_element = None
                for link_selector in link_selectors:
                    try:
                        link_element = await element.query_selector(link_selector)
                        if link_element:
                            break
                    except Exception:
                        continue
                
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href:
                        # Make sure URL is absolute
                        if href.startswith("/"):
                            full_url = f"{self.config['base_url']}{href}"
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            full_url = f"{self.config['base_url']}/{href}"
                        
                        # Check if it's a product URL (for Best Buy Canada contains /en-ca/product/)
                        if "/en-ca/product/" in full_url:
                            product_links.append(full_url)
            except Exception as e:
                logger.warning(f"Error extracting product link: {str(e)}")
        
        logger.info(f"Found {len(product_links)} product links")
        return product_links
    
    async def _extract_links_general_approach(self, page) -> List[str]:
        """
        A more general approach to extract product links when specific selectors fail.
        
        Args:
            page: The Playwright page object
            
        Returns:
            A list of product URLs
        """
        product_links = []
        
        try:
            # Get all links on the page
            all_links = await page.query_selector_all("a[href]")
            logger.info(f"Found {len(all_links)} total links on the page")
            
            # Filter for likely product links
            for link in all_links:
                href = await link.get_attribute("href")
                if href:
                    # Check if it's likely a product URL
                    if ("/shop/" in href or "/skava/" in href or "/site/" in href) and not ("/category/" in href or "/department/" in href):
                        if href.startswith("/"):
                            full_url = f"{self.config['base_url']}{href}"
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            full_url = f"{self.config['base_url']}/{href}"
                        product_links.append(full_url)
            
            # Remove duplicates
            product_links = list(set(product_links))
            logger.info(f"Found {len(product_links)} potential product links using general approach")
            
        except Exception as e:
            logger.error(f"Error in general link extraction approach: {str(e)}")
        
        return product_links
    
    async def _scrape_product_details(self, page, url: str) -> Optional[Dict]:
        """
        Scrape details for a single product.
        
        Args:
            page: The Playwright page object
            url: The URL of the product page
            
        Returns:
            A dictionary containing product details or None if scraping failed
        """
        logger.info(f"Scraping product: {url}")
        
        for attempt in range(self.config["max_retries"]):
            try:
                # Use domcontentloaded instead of networkidle for faster loading
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                
                # Check for various page elements to determine when content is loaded - Best Buy Canada selectors
                selectors_to_try = [
                    "h1[data-automation='product-title']", 
                    ".productName_2KoPa",
                    ".title_2HhVQ",
                    ".name_1EVxY",
                    "h1.title_3a6Uh",
                    "h1"
                ]
                
                title_selector = None
                for selector in selectors_to_try:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        title_selector = selector
                        logger.info(f"Found product title with selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if not title_selector:
                    logger.warning("Could not find product title element, taking a screenshot for debugging")
                    await page.screenshot(path=f"product_debug_{attempt}.png")
                    raise Exception("Product title element not found")
                
                # Extract product details using various potential selectors - Best Buy Canada selectors
                title = ""
                title_selectors = [
                    "h1[data-automation='product-title']", 
                    ".productName_2KoPa",
                    ".title_2HhVQ",
                    ".name_1EVxY",
                    "h1.title_3a6Uh",
                    "h1"
                ]
                for selector in title_selectors:
                    title = await self._get_text(page, selector)
                    if title:
                        break
                
                # Try different price selectors - Best Buy Canada selectors
                price_raw = ""
                price_selectors = [
                    "span[data-automation='product-price']",
                    ".price_FHDfG",
                    ".pricingContainer_3WJwK span",
                    ".large-price_3CcV5",
                    ".regularPrice_30e83",
                    ".currentPrice_2j0I2"
                ]
                for selector in price_selectors:
                    price_raw = await self._get_text(page, selector)
                    if price_raw:
                        break
                        
                # Clean up price
                price = ""
                if price_raw:
                    # Extract just the numeric price using regex if needed
                    import re
                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_raw)
                    if price_match:
                        price = price_match.group(1).replace(",", "")
                    else:
                        price = price_raw.replace("$", "").replace(",", "").strip()
                
                # Try different description selectors - Best Buy Canada selectors
                description = ""
                desc_selectors = [
                    "div[data-automation='productDescription']",
                    ".description_1GJqI",
                    ".shortDesc_2Jskd",
                    ".productDesc_DsbNy",
                    ".overview_3fZXP",
                    ".tab-overview"
                ]
                for selector in desc_selectors:
                    description = await self._get_text(page, selector)
                    if description:
                        break
                
                # If still no description, try getting the meta description
                if not description:
                    try:
                        description = await page.evaluate(
                            "() => document.querySelector('meta[name=\"description\"]')?.getAttribute('content') || ''"
                        )
                    except Exception:
                        pass
                
                # Extract specifications
                specs = await self._extract_specifications(page)
                
                # Extract rating using different selectors - Best Buy Canada selectors
                rating = "Not rated"
                rating_selectors = [
                    "span[data-automation='reviewsStarRating']",
                    ".rating_2WbU5",
                    ".ratingContainer_3zFk8 span",
                    ".rating-wrapper span",
                    ".review-rating-value"
                ]
                for selector in rating_selectors:
                    rating_text = await self._get_text(page, selector)
                    if rating_text:
                        # Try to extract just the numeric rating
                        import re
                        rating_match = re.search(r'([\d\.]+)', rating_text)
                        if rating_match:
                            rating = rating_match.group(1)
                        else:
                            rating = rating_text
                        break
                
                # Extract image URL using different selectors
                image_url = await self._get_image_url(page)
                
                # Extract unique identifier from URL
                try:
                    # Try to get a unique identifier from the URL
                    product_id = ""
                    url_parts = url.split("/")
                    for part in url_parts:
                        if ".p" in part:
                            product_id = part.split(".p")[0]
                            break
                    
                    if not product_id and len(url_parts) > 1:
                        product_id = url_parts[-1].split(".")[0]
                        
                    if not product_id:
                        # Generate a hash from the URL
                        import hashlib
                        product_id = hashlib.md5(url.encode()).hexdigest()[:12]
                except Exception:
                    # If all else fails, use a hash of the URL
                    import hashlib
                    product_id = hashlib.md5(url.encode()).hexdigest()[:12]
                
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
                    "category": self.config["categories"][self.category]["name"],
                    "scraped_at": datetime.now().isoformat(),
                }
                
                # Only return if we have at least a title
                if title:
                    return product_data
                else:
                    logger.warning(f"Failed to extract title for product at {url}, retrying...")
                    continue
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed for {url}: {str(e)}")
                if attempt < self.config["max_retries"] - 1:
                    # Add increasing delay between retries
                    await asyncio.sleep((attempt + 1) * self.config["request_delay"])
        
        logger.error(f"Failed to scrape product after {self.config['max_retries']} attempts: {url}")
        return None
    
    async def _extract_specifications(self, page) -> Dict:
        """
        Extract product specifications from the product page.
        
        Args:
            page: The Playwright page object
            
        Returns:
            A dictionary of specifications
        """
        specs = {}
        
        try:
            # First try if there's a specifications tab that needs to be clicked
            spec_tab_selectors = [
                "button[data-automation='specifications-tab']",
                "button[data-automation='specifications']",
                "button:has-text('Specifications')",
                "button:has-text('Specs')",
                ".tab-specifications",
                "[data-id='specifications']"
            ]
            
            for selector in spec_tab_selectors:
                try:
                    spec_tab = await page.query_selector(selector)
                    if spec_tab:
                        await spec_tab.click()
                        # Wait a moment for specs to load
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
            
            # Look for specifications in different formats - Best Buy Canada
            
            # Format 1: Table format
            spec_table_selectors = [
                "table.specifications",
                "div[data-automation='specifications-content'] table",
                ".specs-table",
                ".specification-table"
            ]
            
            for table_selector in spec_table_selectors:
                spec_rows = await page.query_selector_all(f"{table_selector} tr")
                if spec_rows and len(spec_rows) > 0:
                    for row in spec_rows:
                        name_elem = await row.query_selector("td:first-child, th:first-child")
                        value_elem = await row.query_selector("td:nth-child(2), th:nth-child(2)")
                        
                        if name_elem and value_elem:
                            name = await name_elem.inner_text()
                            value = await value_elem.inner_text()
                            if name.strip() and value.strip():
                                specs[name.strip()] = value.strip()
            
            # Format 2: Definition list format
            spec_dl_selectors = [
                "dl.specification-list",
                "div[data-automation='specifications-content'] dl",
                ".specs-list",
                ".spec-list"
            ]
            
            for dl_selector in spec_dl_selectors:
                dl_elements = await page.query_selector_all(dl_selector)
                for dl in dl_elements:
                    dt_elements = await dl.query_selector_all("dt")
                    dd_elements = await dl.query_selector_all("dd")
                    
                    for i in range(min(len(dt_elements), len(dd_elements))):
                        name = await dt_elements[i].inner_text()
                        value = await dd_elements[i].inner_text()
                        if name.strip() and value.strip():
                            specs[name.strip()] = value.strip()
            
            # Format 3: Div-based format with labels and values
            spec_div_selectors = [
                "div[data-automation='specifications-content'] .specification-item",
                ".specificationAttribute_1Vhbw",
                ".specificationRow_2RnDN",
                ".spec-group-item"
            ]
            
            for div_selector in spec_div_selectors:
                spec_divs = await page.query_selector_all(div_selector)
                for spec_div in spec_divs:
                    label_selectors = [".name_12Ixn", ".label", ".spec-label", ".key_30Yrk"]
                    value_selectors = [".value_2Y5HS", ".value", ".spec-value", ".value_3dHrV"]
                    
                    name = ""
                    value = ""
                    
                    for label_selector in label_selectors:
                        label_elem = await spec_div.query_selector(label_selector)
                        if label_elem:
                            name = await label_elem.inner_text()
                            break
                    
                    for value_selector in value_selectors:
                        value_elem = await spec_div.query_selector(value_selector)
                        if value_elem:
                            value = await value_elem.inner_text()
                            break
                    
                    if name.strip() and value.strip():
                        specs[name.strip()] = value.strip()
                    
        except Exception as e:
            logger.warning(f"Error extracting specifications: {str(e)}")
        
        return specs
    
    async def _get_text(self, page, selector: str) -> str:
        """
        Helper method to get text from an element.
        
        Args:
            page: The Playwright page object
            selector: The CSS selector for the element
            
        Returns:
            The text content of the element or an empty string if not found
        """
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.inner_text()
        except Exception as e:
            logger.debug(f"Error getting text from {selector}: {str(e)}")
        return ""
    
    async def _get_image_url(self, page) -> str:
        """
        Helper method to get the product image URL.
        
        Args:
            page: The Playwright page object
            
        Returns:
            The URL of the product image or an empty string if not found
        """
        try:
            # Try Best Buy Canada image selectors
            image_selectors = [
                "img[data-automation='image-gallery-main-image']",
                ".productGallery_1jeLb img",
                ".gallery_1nJpr img",
                ".mainImage_3Vlhh",
                ".mainImage_2G_xj img",
                "[data-automation='product-image']"
            ]
            
            for selector in image_selectors:
                image_element = await page.query_selector(selector)
                if image_element:
                    src = await image_element.get_attribute("src")
                    if src:
                        return src
            
            # If no specific selectors work, try to find any product image
            all_images = await page.query_selector_all("img")
            for img in all_images:
                src = await img.get_attribute("src")
                if src and ("product" in src.lower() or "item" in src.lower()):
                    return src
                
        except Exception as e:
            logger.debug(f"Error getting image URL: {str(e)}")
        return ""
    
    def _save_data(self) -> None:
        """
        Save the scraped data to a JSON file.
        """
        if not self.products:
            logger.warning("No products to save")
            return
        
        output_file = DATA_PATHS["scraped_data"]
        logger.info(f"Saving {len(self.products)} products to {output_file}")
        
        with open(output_file, "w") as f:
            json.dump(self.products, f, indent=2)
        
        logger.info(f"Data saved to {output_file}")


async def main(category: str, count: int, headless: bool) -> None:
    """
    Main function to run the scraper.
    
    Args:
        category: The product category to scrape
        count: The number of products to scrape
        headless: Whether to run the browser in headless mode
    """
    scraper = BestBuyScraper(category=category, count=count, headless=headless)
    products = await scraper.start()
    
    if products:
        print(f"\nSuccessfully scraped {len(products)} products from Best Buy.")
        print(f"Data saved to {DATA_PATHS['scraped_data']}")
    else:
        print("No products were scraped. Check the logs for details.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape product data from Best Buy")
    parser.add_argument(
        "--category",
        type=str,
        default="computers_tablets",
        choices=SCRAPER_CONFIG["BESTBUY"]["categories"].keys(),
        help="Product category to scrape",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of products to scrape",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--visible",
        action="store_false",
        dest="headless",
        help="Run browser in visible mode (not headless)",
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(args.category, args.count, args.headless))
