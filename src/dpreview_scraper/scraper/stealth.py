"""Anti-detection and Cloudflare challenge handling."""

import asyncio
import random

from playwright.async_api import Page

from dpreview_scraper.utils.logging import logger

# Cloudflare bypass configuration
CLOUDFLARE_CHALLENGE_INDICATOR = "just a moment"
CLOUDFLARE_MAX_WAIT_SECONDS = 60


async def check_and_dismiss_cookie_popup(page: Page) -> bool:
    """Check for and attempt to dismiss cookie consent popup.

    Args:
        page: Playwright page

    Returns:
        True if popup was found and dismissed, False otherwise
    """
    try:
        cookie_selectors = [
            'button[id*="accept"]',
            'button[class*="accept"]',
            'button:has-text("Accept")',
            'button:has-text("I Accept")',
            'button:has-text("Got it")',
            '[id*="cookie"] button',
            '[class*="consent"] button',
        ]

        for selector in cookie_selectors:
            try:
                button = await page.query_selector(selector)
                if button:
                    logger.debug(f"[COOKIE] Found cookie popup button with selector: {selector}")
                    await button.click()
                    logger.debug("[COOKIE] Clicked cookie accept button")
                    await asyncio.sleep(1)
                    return True
            except Exception as e:
                logger.debug(f"[COOKIE] Could not click selector {selector}: {e}")

        logger.debug("[COOKIE] No cookie popup found")
        return False

    except Exception as e:
        logger.debug(f"[COOKIE] Error checking for cookie popup: {e}")
        return False


async def wait_for_cloudflare_challenge(
    page: Page, max_wait_seconds: int = CLOUDFLARE_MAX_WAIT_SECONDS
) -> bool:
    """Wait for Cloudflare challenge to complete with human-like behavior.

    Simulates mouse movement, scrolling, and waits for the challenge page
    title to change, indicating the challenge has been resolved.

    Args:
        page: Playwright page
        max_wait_seconds: Maximum time to wait for challenge

    Returns:
        True if challenge resolved, False if still blocked
    """
    try:
        title = await page.title()
        logger.debug(f"[CLOUDFLARE] Current page title: '{title}'")

        if CLOUDFLARE_CHALLENGE_INDICATOR not in title.lower():
            logger.debug("[CLOUDFLARE] No challenge detected - page loaded successfully")
            try:
                cookie_popup = await page.query_selector(
                    '[id*="cookie"], [class*="cookie"], [class*="consent"]'
                )
                if cookie_popup:
                    logger.debug("[COOKIE] Cookie consent popup detected on page")
            except Exception as e:
                logger.debug(f"[COOKIE] Error checking for cookie popup: {e}")
            return True

        logger.warning(
            f"[CLOUDFLARE] Challenge detected! Waiting up to {max_wait_seconds}s for resolution..."
        )

        # Random initial delay
        await asyncio.sleep(random.uniform(2, 4))

        # Simulate mouse movement
        try:
            viewport_size = page.viewport_size
            if viewport_size:
                for _ in range(3):
                    x = random.randint(100, viewport_size["width"] - 100)
                    y = random.randint(100, viewport_size["height"] - 100)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            logger.debug(f"Mouse movement simulation failed: {e}")

        # Scroll down slowly to simulate reading
        try:
            scroll_steps = [100, 250, 400, 300, 150]
            for scroll_y in scroll_steps:
                await page.evaluate(
                    f"window.scrollTo({{ top: {scroll_y}, behavior: 'smooth' }})"
                )
                await asyncio.sleep(random.uniform(0.3, 0.8))

            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await asyncio.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            logger.debug(f"Scroll simulation failed: {e}")

        # Wait for title to change (challenge completed)
        start_time = asyncio.get_event_loop().time()
        check_interval = 1

        while (asyncio.get_event_loop().time() - start_time) < max_wait_seconds:
            await asyncio.sleep(check_interval)

            current_title = await page.title()
            if CLOUDFLARE_CHALLENGE_INDICATOR not in current_title.lower():
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.info(f"[CLOUDFLARE] Challenge resolved successfully after {elapsed:.1f}s!")
                await asyncio.sleep(random.uniform(1.5, 3.0))
                return True

        logger.warning(f"[CLOUDFLARE] Challenge FAILED - timeout after {max_wait_seconds}s")
        logger.debug("[CLOUDFLARE] Will fall back to basic specs without review data")
        return False

    except Exception as e:
        logger.debug(f"Error waiting for Cloudflare challenge: {e}")
        return False
