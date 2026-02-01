"""Product page scraper."""

from typing import Optional
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from dpreview_scraper.config import settings
from dpreview_scraper.models.camera import Camera, SearchResult
from dpreview_scraper.parsers.product_parser import parse_product_page
from dpreview_scraper.scraper.browser import BrowserManager
from dpreview_scraper.utils.rate_limiter import RateLimiter
from dpreview_scraper.utils.logging import logger


class ProductScraper:
    """Scraper for individual product pages."""

    def __init__(
        self,
        browser_manager: BrowserManager,
        rate_limiter: RateLimiter,
    ):
        """Initialize product scraper.

        Args:
            browser_manager: Browser manager instance
            rate_limiter: Rate limiter instance
        """
        self.browser = browser_manager
        self.rate_limiter = rate_limiter

    def _extract_review_url(self, html: str, product_code: str) -> Optional[str]:
        """Extract review URL from product overview HTML.

        Args:
            html: Product overview page HTML
            product_code: Product code for logging

        Returns:
            Review URL or None if not found
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            review_link = soup.select_one('a.actionButtonLink[href*="/reviews/"]')

            if review_link:
                href = review_link.get("href")
                if href:
                    # Make URL absolute if needed
                    if not href.startswith("http"):
                        return f"{settings.base_url}{href}"
                    return href

            logger.debug(f"No review link found in HTML for {product_code}")
            return None

        except Exception as e:
            logger.debug(f"Error extracting review URL for {product_code}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((PlaywrightTimeoutError, ConnectionError)),
    )
    async def scrape_product(self, search_result: SearchResult) -> Optional[Camera]:
        """Scrape a single product page.

        Args:
            search_result: Search result with product info

        Returns:
            Camera object with full data, or None if scraping failed
        """
        await self.rate_limiter.acquire()

        url = search_result.url
        if not url.startswith("http"):
            url = f"{settings.base_url}{url}"

        logger.info(f"Scraping product: {search_result.name} ({search_result.product_code})")

        try:
            async with self.browser.new_page() as page:
                # Navigate to product overview page
                await page.goto(url, wait_until="networkidle", timeout=settings.browser_timeout)

                # Wait for main content - quick specs table on overview page
                try:
                    await page.wait_for_selector(
                        "div.rightColumn.quickSpecs table",
                        timeout=10000,
                    )
                except PlaywrightTimeoutError:
                    logger.warning(f"Timeout waiting for overview content: {search_result.product_code}")

                # Get overview page content
                overview_html = await page.content()

                # Navigate to specifications page for full specs
                specs_url = f"{url}/specifications"
                logger.debug(f"Fetching specifications from: {specs_url}")

                await self.rate_limiter.acquire()
                await page.goto(specs_url, wait_until="networkidle", timeout=settings.browser_timeout)

                # Wait for specs table
                try:
                    await page.wait_for_selector(
                        "table.specsTable.compact",
                        timeout=10000,
                    )
                except PlaywrightTimeoutError:
                    logger.warning(f"Timeout waiting for specs table: {search_result.product_code}")

                # Get specifications page content
                specs_html = await page.content()

                # Extract review URL from overview HTML (already fetched)
                review_html = None
                review_url = self._extract_review_url(overview_html, search_result.product_code)

                if review_url:
                    logger.debug(f"Fetching review from: {review_url}")

                    try:
                        await self.rate_limiter.acquire()
                        await page.goto(review_url, wait_until="networkidle", timeout=settings.browser_timeout)

                        # Wait for review content
                        try:
                            await page.wait_for_selector("div.article", timeout=10000)
                        except PlaywrightTimeoutError:
                            logger.debug(f"Timeout waiting for review content: {search_result.product_code}")

                        review_html = await page.content()
                        logger.debug(f"Successfully fetched review page for {search_result.product_code}")
                    except Exception as e:
                        logger.debug(f"No review page available for {search_result.product_code}: {e}")
                else:
                    logger.debug(f"No review link found for {search_result.product_code}")

                # Parse product data from all pages
                camera = parse_product_page(
                    overview_html,
                    specs_html,
                    review_html,
                    product_code=search_result.product_code,
                    url=search_result.url,
                )

                # Fill in data from search result if missing
                if not camera.Name:
                    camera.Name = search_result.name
                if not camera.ImageURL:
                    camera.ImageURL = search_result.image_url
                if search_result.announced and not camera.Specs.Announced:
                    camera.Specs.Announced = search_result.announced

                logger.info(f"Successfully scraped: {search_result.product_code}")
                return camera

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout scraping {search_result.product_code}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to scrape {search_result.product_code}: {e}")
            return None
