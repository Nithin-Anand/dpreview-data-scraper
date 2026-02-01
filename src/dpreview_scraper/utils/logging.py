"""Logging configuration."""

import logging
import sys
from rich.logging import RichHandler
from rich.console import Console

console = Console()


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging with Rich handler.

    Args:
        verbose: Enable verbose logging

    Returns:
        Configured logger
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=verbose,
            )
        ],
    )

    # Return logger for this package
    logger = logging.getLogger("dpreview_scraper")
    logger.setLevel(level)

    return logger


# Package-level logger
logger = setup_logging()
