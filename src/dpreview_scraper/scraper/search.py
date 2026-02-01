"""Search page scraper."""

from datetime import datetime
from typing import List, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from dpreview_scraper.config import settings
from dpreview_scraper.models.camera import SearchResult
from dpreview_scraper.parsers.search_parser import parse_search_results, extract_pagination_info
from dpreview_scraper.scraper.browser import BrowserManager
from dpreview_scraper.utils.rate_limiter import RateLimiter
from dpreview_scraper.utils.logging import logger


class SearchScraper:
    """Scraper for DPReview camera search page."""

    def __init__(
        self,
        browser_manager: BrowserManager,
        rate_limiter: RateLimiter,
        after_date: Optional[str] = None,
    ):
        """Initialize search scraper.

        Args:
            browser_manager: Browser manager instance
            rate_limiter: Rate limiter instance
            after_date: Only include cameras announced after this date (YYYY-MM-DD)
        """
        self.browser = browser_manager
        self.rate_limiter = rate_limiter
        self.after_date = after_date or settings.after_date

        # Parse date for filtering
        try:
            self.after_datetime = datetime.strptime(self.after_date, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid after_date format: {self.after_date}, using default")
            self.after_datetime = datetime.strptime(settings.after_date, "%Y-%m-%d")

    async def scrape_all_pages(
        self, max_pages: Optional[int] = None
    ) -> List[SearchResult]:
        """Scrape all search result pages.

        Args:
            max_pages: Maximum number of pages to scrape (None for all)

        Returns:
            List of all search results
        """
        all_results = []
        page_num = 1

        logger.info("Starting search page scraping")

        while True:
            if max_pages and page_num > max_pages:
                logger.info(f"Reached max pages limit: {max_pages}")
                break

            logger.info(f"Scraping search page {page_num}")

            try:
                results, has_next = await self.scrape_page(page_num)
                all_results.extend(results)

                logger.info(f"Found {len(results)} cameras on page {page_num}")

                # Stop if no more pages or no results found
                if not has_next:
                    logger.info("No more pages")
                    break

                if len(results) == 0:
                    logger.info("No results found, stopping pagination")
                    break

                page_num += 1

            except Exception as e:
                logger.error(f"Failed to scrape page {page_num}: {e}")
                break

        # Filter by date
        filtered_results = self._filter_by_date(all_results)

        logger.info(
            f"Total cameras found: {len(all_results)}, "
            f"after filtering: {len(filtered_results)}"
        )

        return filtered_results

    async def scrape_page(self, page_num: int = 1) -> tuple[List[SearchResult], bool]:
        """Scrape a single search results page.

        Args:
            page_num: Page number to scrape

        Returns:
            Tuple of (search results, has_next_page)
        """
        await self.rate_limiter.acquire()

        # Use query parameter for pagination
        # search_url already has ?view=list, so add &page=N for subsequent pages
        if page_num == 1:
            url = settings.search_url
        else:
            url = f"{settings.search_url}&page={page_num}"

        async with self.browser.new_page() as page:
            try:
                # Navigate to search page
                await page.goto(url, wait_until="networkidle", timeout=settings.browser_timeout)

                # Wait for product list to load
                # The search page uses a table structure with class "productList"
                try:
                    await page.wait_for_selector(
                        "table.productList tr.product",
                        timeout=10000,
                    )
                except PlaywrightTimeoutError:
                    logger.warning(f"Timeout waiting for products on page {page_num}")

                # Get page content
                html = await page.content()

                # Parse results
                results = parse_search_results(html)

                # Check pagination
                pagination_info = extract_pagination_info(html)
                has_next = pagination_info.get("has_next", False)

                return results, has_next

            except PlaywrightTimeoutError:
                logger.error(f"Page timeout on page {page_num}")
                return [], False
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                raise

    def _filter_by_date(self, results: List[SearchResult]) -> List[SearchResult]:
        """Filter results by announcement date.

        Args:
            results: List of search results

        Returns:
            Filtered list
        """
        filtered = []

        for result in results:
            if not result.announced:
                # Include if no date info
                filtered.append(result)
                continue

            try:
                # Try to parse various date formats
                announced_date = None

                # Try ISO format first
                for fmt in ["%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%Y-%m", "%b %Y"]:
                    try:
                        announced_date = datetime.strptime(result.announced, fmt)
                        break
                    except ValueError:
                        continue

                if announced_date and announced_date >= self.after_datetime:
                    filtered.append(result)
                elif not announced_date:
                    # Couldn't parse date, include it
                    logger.debug(f"Could not parse date for {result.product_code}: {result.announced}")
                    filtered.append(result)

            except Exception as e:
                logger.warning(f"Error filtering {result.product_code} by date: {e}")
                filtered.append(result)

        return filtered
