"""Progress tracking for resumable scraping."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from dpreview_scraper.utils.logging import logger


class ProgressTracker:
    """Track scraping progress for resumability."""

    def __init__(self, progress_file: Path):
        """Initialize progress tracker.

        Args:
            progress_file: Path to progress JSON file
        """
        self.progress_file = Path(progress_file)
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()
        self.total: int = 0
        self.started_at: str = ""
        self.last_updated: str = ""

        self._load()

    def _load(self) -> None:
        """Load progress from file."""
        if not self.progress_file.exists():
            return

        try:
            with open(self.progress_file, "r") as f:
                data = json.load(f)

            self.completed = set(data.get("completed", []))
            self.failed = set(data.get("failed", []))
            self.total = data.get("total", 0)
            self.started_at = data.get("started_at", "")
            self.last_updated = data.get("last_updated", "")

            logger.info(
                f"Loaded progress: {len(self.completed)} completed, "
                f"{len(self.failed)} failed, {self.total} total"
            )

        except Exception as e:
            logger.warning(f"Failed to load progress file: {e}")

    def save(self) -> None:
        """Save progress to file."""
        self.last_updated = datetime.now().isoformat()

        data = {
            "completed": sorted(list(self.completed)),
            "failed": sorted(list(self.failed)),
            "total": self.total,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
        }

        try:
            with open(self.progress_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress file: {e}")

    def start(self, total: int) -> None:
        """Mark scraping as started.

        Args:
            total: Total number of items to scrape
        """
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        self.total = total
        self.save()

    def mark_completed(self, product_code: str) -> None:
        """Mark product as successfully scraped.

        Args:
            product_code: Product code
        """
        self.completed.add(product_code)
        # Remove from failed if it was there
        self.failed.discard(product_code)
        self.save()

    def mark_failed(self, product_code: str) -> None:
        """Mark product as failed.

        Args:
            product_code: Product code
        """
        self.failed.add(product_code)
        self.save()

    def is_completed(self, product_code: str) -> bool:
        """Check if product was already scraped.

        Args:
            product_code: Product code

        Returns:
            True if already completed
        """
        return product_code in self.completed

    def get_remaining(self, all_products: List[str]) -> List[str]:
        """Get list of products not yet completed.

        Args:
            all_products: All product codes

        Returns:
            List of product codes to scrape
        """
        return [p for p in all_products if p not in self.completed]

    def get_stats(self) -> Dict[str, any]:
        """Get progress statistics.

        Returns:
            Dict with progress stats
        """
        remaining = self.total - len(self.completed)
        progress_pct = (len(self.completed) / self.total * 100) if self.total > 0 else 0

        return {
            "total": self.total,
            "completed": len(self.completed),
            "failed": len(self.failed),
            "remaining": remaining,
            "progress_percent": round(progress_pct, 1),
            "started_at": self.started_at,
            "last_updated": self.last_updated,
        }

    def clear(self) -> None:
        """Clear progress and delete file."""
        self.completed.clear()
        self.failed.clear()
        self.total = 0
        self.started_at = ""
        self.last_updated = ""

        if self.progress_file.exists():
            self.progress_file.unlink()

        logger.info("Cleared progress")
