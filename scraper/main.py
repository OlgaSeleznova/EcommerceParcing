"""
Main script for the Best Buy scraper.

This script uses the utility functions to scrape product data from Best Buy.
"""
import asyncio
import os
import sys
from playwright.async_api import async_playwright
import random


# Add the parent directory to the path to import from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tqdm import tqdm
from config import SCRAPER_CONFIG, DATA_PATHS
from scraper.utils import (
    setup_logger,
    extract_product_urls,
    scrape_single_product,
    save_data,
    parse_args
)


async def main():
    """
    Main function to run the scraper.
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Set up logger
    logger = setup_logger(__name__)
    logger.info(f"Starting Best Buy scraper")
    
    products = []
    
    # Get the category URL by looking up the category slug
    category_url = None
    for category in SCRAPER_CONFIG[args.source]["categories"]:
        if category["slug"] == args.category:
            category_url = category["url"]
            logger.info(f"Using category: {args.category} with URL: {category_url}")
            break
    
    # If the category is not found in the config, raise an error
    if category_url is None:
        available_categories = ", ".join([cat["slug"] for cat in SCRAPER_CONFIG[args.source]["categories"]])
        error_msg = f"Error: Category '{args.category}' not found in config. Available categories: {available_categories}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    async with async_playwright() as p:
        # Launch with more robust settings
        browser = await p.chromium.launch(headless=args.headless, timeout=60000)
        # Select a random user agent from the list
        selected_user_agent = random.choice(SCRAPER_CONFIG[args.source]["user_agent"])
        logger.info(f"Using user agent: {selected_user_agent[:50]}...")
        
        context = await browser.new_context(
            user_agent=selected_user_agent,
            viewport={"width": 1920, "height": 1080},
        )
        
        # Set custom headers
        await context.set_extra_http_headers(SCRAPER_CONFIG[args.source]["headers"])
        
        # Add a small delay to ensure proper initialization
        await asyncio.sleep(1)
        
        # Create a new page with longer default timeout
        page = await context.new_page()
        page.set_default_timeout(30000)
        
        try:
            # Navigate to the category page
            logger.info(f"Navigating to: {category_url}")
            await page.goto(category_url, timeout=60000)
            
            # Find product elements
            product_selectors = [
                ".x-productListItem",
                "div[class*='productLine']",
                "div[class*='product-item']",
                ".product-listing"
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
            product_links = await extract_product_urls(page, logger, args.source)
            
            if not product_links:
                logger.error("No product links found. Taking screenshot for debugging.")
                return []
            
            # Limit to the number requested
            product_links = product_links[:args.count]
            
            # Use tqdm for progress bar when running in a terminal
            for url in tqdm(product_links, desc="Scraping products"):
                # Try multiple times in case of errors
                for attempt in range(3):
                    try:
                        product_data = await scrape_single_product(page, url, args.source, logger, args.category)
                        if product_data:
                            products.append(product_data)
                            break
                    except Exception as e:
                        logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
                        if attempt == 2:  # Last attempt
                            logger.error(f"Failed to scrape product after 3 attempts: {url}")
                        else:
                            # Wait and retry
                            await page.wait_for_timeout(2000)
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            # Close the browser
            await browser.close()
    
    # Save the scraped data
    if products:
        save_data(products, DATA_PATHS["scraped_data"], logger)
        print(f"\nSuccessfully scraped {len(products)} products from Best Buy")
        print(f"Data saved to {DATA_PATHS['scraped_data']}")
    else:
        print("No products were scraped. Check the logs for details.")
    
    return products


if __name__ == "__main__":
    asyncio.run(main())
