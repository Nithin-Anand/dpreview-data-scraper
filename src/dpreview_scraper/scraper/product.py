"""Product page scraper."""

import asyncio
import random
from typing import Optional
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from dpreview_scraper.config import settings
from dpreview_scraper.models.camera import Camera, SearchResult
from dpreview_scraper.parsers.product_parser import parse_product_page
from dpreview_scraper.scraper.browser import BrowserManager
from dpreview_scraper.scraper.stealth import (
    CLOUDFLARE_CHALLENGE_INDICATOR,
    check_and_dismiss_cookie_popup,
    wait_for_cloudflare_challenge,
)
from dpreview_scraper.utils.rate_limiter import RateLimiter
from dpreview_scraper.utils.logging import logger

PAGE_LOAD_TIMEOUT_MS = 15000
REVIEW_PAGE_EXTRA_DELAY = (3, 6)  # Random delay range (min, max) before review pages


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
                        timeout=PAGE_LOAD_TIMEOUT_MS,
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
                        timeout=PAGE_LOAD_TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    logger.warning(f"Timeout waiting for specs table: {search_result.product_code}")

                # Get specifications page content
                specs_html = await page.content()

                # Extract review URL from overview HTML (already fetched)
                review_html = None
                review_specs_html = None
                review_url = self._extract_review_url(overview_html, search_result.product_code)

                if review_url:
                    logger.debug(f"Fetching review from: {review_url}")
                    logger.debug(f"[CLOUDFLARE] Attempting to fetch review page for {search_result.product_code}")

                    try:
                        # Extra delay before review pages (reviews are more heavily protected)
                        extra_delay = random.uniform(*REVIEW_PAGE_EXTRA_DELAY)
                        logger.debug(f"Adding extra delay of {extra_delay:.1f}s before review page")
                        await asyncio.sleep(extra_delay)

                        await self.rate_limiter.acquire()

                        # Use domcontentloaded instead of networkidle for faster initial load
                        await page.goto(review_url, wait_until="domcontentloaded", timeout=60000)

                        # Check for and dismiss cookie popup first
                        await check_and_dismiss_cookie_popup(page)

                        # Wait for Cloudflare challenge to resolve
                        logger.debug(f"[CLOUDFLARE] Checking for Cloudflare challenge on review page")
                        challenge_resolved = await wait_for_cloudflare_challenge(page)

                        if not challenge_resolved:
                            logger.warning(
                                f"[CLOUDFLARE] Challenge NOT resolved for {search_result.product_code} - "
                                f"USING FALLBACK MODE (basic specs only)"
                            )
                            logger.debug(
                                f"[FALLBACK] Skipping review content for {search_result.product_code}. "
                                f"Detailed video modes and review data will not be available."
                            )
                            # Skip review content and continue with basic specs
                            review_html = None
                            review_specs_html = None
                        else:
                            # Challenge resolved, proceed with fetching review content
                            logger.debug(f"[CLOUDFLARE] Challenge resolved successfully for {search_result.product_code}")
                            # Wait for review content
                            try:
                                await page.wait_for_selector("div.article", timeout=PAGE_LOAD_TIMEOUT_MS)
                                logger.debug(f"Review article content found for {search_result.product_code}")
                            except PlaywrightTimeoutError:
                                logger.debug(f"Timeout waiting for review article: {search_result.product_code}")

                            review_html = await page.content()

                            # Verify we actually got review content and not Cloudflare page
                            if CLOUDFLARE_CHALLENGE_INDICATOR in (await page.title()).lower():
                                logger.warning(
                                    f"[CLOUDFLARE] Still blocked on Cloudflare page for {search_result.product_code} - "
                                    f"USING FALLBACK MODE"
                                )
                                logger.debug(f"[FALLBACK] Review content unavailable, using basic specs only")
                                review_html = None
                            else:
                                logger.debug(f"[SUCCESS] Review page fetched successfully for {search_result.product_code}")

                                # Fetch review page 2 (specs page) - more comprehensive specs
                                review_specs_url = f"{review_url}/2"
                                logger.debug(f"Fetching review specs from: {review_specs_url}")

                                try:
                                    # Extra delay before review specs page
                                    extra_delay = random.uniform(*REVIEW_PAGE_EXTRA_DELAY)
                                    logger.debug(f"Adding extra delay of {extra_delay:.1f}s before review specs page")
                                    await asyncio.sleep(extra_delay)

                                    await self.rate_limiter.acquire()
                                    await page.goto(review_specs_url, wait_until="domcontentloaded", timeout=60000)

                                    # Check for cookie popup on specs page too
                                    await check_and_dismiss_cookie_popup(page)

                                    # Wait for specs content
                                    try:
                                        await page.wait_for_selector("table.contentTable", timeout=PAGE_LOAD_TIMEOUT_MS)
                                        logger.debug(f"Review specs table found for {search_result.product_code}")
                                    except PlaywrightTimeoutError:
                                        logger.debug(f"Timeout waiting for review specs table: {search_result.product_code}")

                                    review_specs_html = await page.content()

                                except Exception as e:
                                    logger.debug(f"No review specs page available for {search_result.product_code}: {e}")

                    except Exception as e:
                        logger.debug(f"No review page available for {search_result.product_code}: {e}")
                else:
                    logger.debug(f"No review link found for {search_result.product_code}")

                # Log data sources being used
                data_sources = []
                if overview_html:
                    data_sources.append("overview")
                if specs_html:
                    data_sources.append("specs")
                if review_html:
                    data_sources.append("review")
                if review_specs_html:
                    data_sources.append("review_specs")

                logger.debug(f"[DATA SOURCES] Parsing {search_result.product_code} using: {', '.join(data_sources)}")
                if not review_html and not review_specs_html:
                    logger.debug(f"[FALLBACK] Operating in fallback mode - no review data available")

                # Parse product data from all pages
                camera = parse_product_page(
                    overview_html,
                    specs_html,
                    review_html,
                    review_specs_html,
                    product_code=search_result.product_code,
                    url=search_result.url,
                    short_specs=search_result.short_specs,
                )

                # Fill in data from search result if missing
                if not camera.Name:
                    camera.Name = search_result.name
                if not camera.ImageURL:
                    camera.ImageURL = search_result.image_url
                if search_result.announced and not camera.Specs.Announced:
                    camera.Specs.Announced = search_result.announced

                # Store review URL for archive lookup
                if review_url:
                    camera.review_url = review_url

                logger.info(f"Successfully scraped: {search_result.product_code}")
                return camera

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout scraping {search_result.product_code}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to scrape {search_result.product_code}: {e}")
            return None
