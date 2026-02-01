"""Wayback Machine archive integration."""

from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from dpreview_scraper.config import settings
from dpreview_scraper.utils.logging import logger


class ArchiveManager:
    """Manage Wayback Machine archive URLs."""

    WAYBACK_AVAILABILITY_API = "https://archive.org/wayback/available"
    WAYBACK_SAVE_API = "https://web.archive.org/save"

    def __init__(self):
        """Initialize archive manager."""
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_archive_url(self, url: str) -> Optional[str]:
        """Get Wayback Machine archive URL for a page.

        Args:
            url: URL to look up

        Returns:
            Archive URL if available, None otherwise
        """
        if not url.startswith("http"):
            url = f"{settings.base_url}{url}"

        try:
            logger.debug(f"Checking Wayback Machine for: {url}")

            response = await self.client.get(
                self.WAYBACK_AVAILABILITY_API,
                params={"url": url},
            )
            response.raise_for_status()

            data = response.json()
            archived_snapshots = data.get("archived_snapshots", {})
            closest = archived_snapshots.get("closest", {})

            if closest and closest.get("available"):
                archive_url = closest.get("url")
                logger.info(f"Found archive URL: {archive_url}")
                return archive_url

            logger.debug(f"No archive found for: {url}")
            return None

        except Exception as e:
            logger.warning(f"Failed to check archive for {url}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def save_to_archive(self, url: str) -> Optional[str]:
        """Request Wayback Machine to archive a URL.

        Args:
            url: URL to archive

        Returns:
            Archive URL if successful, None otherwise
        """
        if not url.startswith("http"):
            url = f"{settings.base_url}{url}"

        try:
            logger.info(f"Requesting archive for: {url}")

            response = await self.client.get(
                f"{self.WAYBACK_SAVE_API}/{url}",
                follow_redirects=True,
            )

            if response.status_code == 200:
                # Archive URL is in the final redirected URL
                archive_url = str(response.url)
                logger.info(f"Archived successfully: {archive_url}")
                return archive_url

            logger.warning(f"Archive request failed with status: {response.status_code}")
            return None

        except Exception as e:
            logger.warning(f"Failed to save archive for {url}: {e}")
            return None

    async def get_or_create_archive(
        self, url: str, create_if_missing: bool = False
    ) -> Optional[str]:
        """Get existing archive or optionally create one.

        Args:
            url: URL to archive
            create_if_missing: If True, create archive if none exists

        Returns:
            Archive URL or None
        """
        # Try to get existing archive
        archive_url = await self.get_archive_url(url)

        if archive_url:
            return archive_url

        # Create if requested
        if create_if_missing:
            logger.info(f"No archive found, creating new one for: {url}")
            archive_url = await self.save_to_archive(url)
            return archive_url

        return None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
