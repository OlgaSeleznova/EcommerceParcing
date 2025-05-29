"""
Best Buy Explorer

This script helps explore the structure of Best Buy's website to identify correct selectors for scraping.
"""
import asyncio
import logging
import os
import sys
from playwright.async_api import async_playwright

# Add the parent directory to the path so we can import from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SCRAPER_CONFIG

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def explore_bestbuy():
    """Explore the structure of Best Buy's website"""
    logger.info("Starting Best Buy explorer")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=SCRAPER_CONFIG["BESTBUY"]["user_agent"],
            viewport={"width": 1920, "height": 1080},
        )
        
        # Add headers to all requests
        await context.set_extra_http_headers(SCRAPER_CONFIG["BESTBUY"]["headers"])
        
        page = await context.new_page()
        
        # Navigate to the laptops category
        category_url = "https://www.bestbuy.com/site/computer-cards-components/video-graphics-cards/abcat0507002.c"
        logger.info(f"Navigating to: {category_url}")
        
        try:
            await page.goto(category_url, wait_until="networkidle")
            logger.info("Page loaded")
            
            # Wait for user to close browser
            logger.info("Browser opened for exploration. Press Enter in the terminal to close...")
            
            # Take a screenshot for reference
            await page.screenshot(path="bestbuy_screenshot.png")
            logger.info("Screenshot saved as bestbuy_screenshot.png")
            
            # Check for product grids or lists
            for selector in [".list-items", ".grid-list", ".product-grid", 
                             ".sku-item-list", ".shop-sku-list"]:
                elements = await page.query_selector_all(selector)
                if elements:
                    logger.info(f"Found potential product container: {selector} ({len(elements)} elements)")
            
            # Check for product items
            for selector in [".list-item", ".grid-item", ".product-item", 
                             ".sku-item", ".shop-sku-grid-item"]:
                elements = await page.query_selector_all(selector)
                if elements:
                    logger.info(f"Found potential product item: {selector} ({len(elements)} elements)")
                    
                    # Check the first element for key product info
                    if elements[0]:
                        logger.info(f"Examining the first {selector} element...")
                        
                        # Check for product title
                        for title_selector in ["h3", "h4", ".sku-title", ".heading-5"]:
                            title_elem = await elements[0].query_selector(title_selector)
                            if title_elem:
                                title = await title_elem.inner_text()
                                logger.info(f"Found potential title with {title_selector}: {title}")
                        
                        # Check for product link
                        for link_selector in ["a", ".image-link", ".product-link"]:
                            link_elem = await elements[0].query_selector(link_selector)
                            if link_elem:
                                href = await link_elem.get_attribute("href")
                                logger.info(f"Found potential link with {link_selector}: {href}")
            
            # Wait for user to observe in the browser
            input()
            
        except Exception as e:
            logger.error(f"Error during exploration: {str(e)}")
        finally:
            await browser.close()
    
    logger.info("Exploration completed")

if __name__ == "__main__":
    asyncio.run(explore_bestbuy())
