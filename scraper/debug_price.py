"""
Debug script for testing the extract_price function in isolation.

This script loads a specific product page and tests only the price extraction logic.
"""
import asyncio
import logging
import os
import sys
import pdb  # Python debugger
from urllib.parse import quote_plus

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SCRAPER_CONFIG
from scraper.utils import extract_price, setup_logger

from playwright.async_api import async_playwright


async def debug_price_extraction(url=None):
    """
    Debug the price extraction function on a specific URL.
    
    Args:
        url: Direct product URL to test
    """
    logger = setup_logger("price_debug")
    logger.setLevel(logging.DEBUG)  # Set to DEBUG for maximum detail
    
    async with async_playwright() as p:
        # Launch browser with visibility for debugging
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=SCRAPER_CONFIG["BestBuy"]["user_agent"],
            viewport={"width": 1920, "height": 1080},
        )
        
        # Set custom headers
        await context.set_extra_http_headers(SCRAPER_CONFIG["BestBuy"]["headers"])
        page = await context.new_page()
        

        # Direct navigation to product page
        logger.info(f"Navigating to: {url}")
        await page.goto(url, timeout=60000)
        
        # Wait for the page to load enough for extraction instead of networkidle
        # First wait for basic DOM content
        await page.wait_for_load_state("domcontentloaded")
        
        # Then wait for a specific element that indicates the page is ready
        try:
            await page.wait_for_selector("h1", timeout=10000)
            logger.info("Product title element found, page appears to be loaded")
        except Exception as e:
            logger.warning(f"Could not find product title element: {e}")
            # Continue anyway
        
        # Get the product title for context
        title_element = await page.query_selector("h1")
        title = await title_element.inner_text() if title_element else "Unknown Product"
        
        logger.info(f"Testing price extraction for: {title}")
        
        # Take a screenshot for reference
        os.makedirs("debug", exist_ok=True)
        screenshot_path = os.path.join("debug", "product_page.png")
        await page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved to: {screenshot_path}")
        
        # Set breakpoint before extracting price
        print("\nAbout to extract price. The debugger will start now.")
        print("Type 'n' to step through code, 'c' to continue to next breakpoint, 'q' to quit")
        pdb.set_trace()  # First breakpoint
        
        # Test the price extraction function
        price = await extract_price(page, logger, title)
        
        # Save HTML for analysis
        html_path = os.path.join("debug", "product_page.html")
        html_content = await page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"HTML saved to: {html_path}")
        
        # Summary of results
        logger.info("=" * 50)
        logger.info(f"PRICE EXTRACTION RESULTS")
        logger.info("=" * 50)
        logger.info(f"Product: {title}")
        logger.info(f"URL: {url}")
        logger.info(f"Extracted Price: {price}")
        logger.info("=" * 50)
        
        # Wait for user to review the page
        print("\nPress Enter to close the browser...")
        await asyncio.sleep(1)  # Small delay
        input()
            

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug the price extraction function")
    parser.add_argument("--url", type=str,default="https://www.bestbuy.ca/en-ca/product/microsoft-surface-laptop-13-copilot-pc-laptop-ocean-snapdragon-x-plus-16gb-ram-512gb-ufs-en/19265464", help="URL of the product page to test")
    
    args = parser.parse_args()
    
    asyncio.run(debug_price_extraction(url=args.url))
