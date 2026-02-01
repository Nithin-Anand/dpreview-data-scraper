"""Playwright browser management."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth.stealth import Stealth

from dpreview_scraper.config import settings
from dpreview_scraper.utils.logging import logger


class BrowserManager:
    """Manages Playwright browser instances with anti-detection measures."""

    def __init__(self, headless: bool = True):
        """Initialize browser manager.

        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._playwright = None

    async def start(self) -> None:
        """Start the browser."""
        if self._browser:
            return

        logger.info("Starting browser...")
        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        logger.info("Browser started")

    async def stop(self) -> None:
        """Stop the browser."""
        if self._browser:
            logger.info("Stopping browser...")
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @asynccontextmanager
    async def new_context(self) -> AsyncIterator[BrowserContext]:
        """Create a new browser context with anti-detection headers.

        Yields:
            Browser context
        """
        if not self._browser:
            await self.start()

        context = await self._browser.new_context(
            user_agent=settings.user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            },
        )

        # Add JavaScript to mask automation
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def new_page(
        self, context: Optional[BrowserContext] = None
    ) -> AsyncIterator[Page]:
        """Create a new page with stealth mode enabled.

        Args:
            context: Optional existing context. If None, creates a new one.

        Yields:
            Browser page with stealth features applied
        """
        stealth = Stealth()

        if context:
            page = await context.new_page()
            await stealth.apply_stealth_async(page)
            try:
                yield page
            finally:
                await page.close()
        else:
            async with self.new_context() as ctx:
                page = await ctx.new_page()
                await stealth.apply_stealth_async(page)
                try:
                    yield page
                finally:
                    await page.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
