"""Configuration management."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Scraping
    base_url: str = "https://www.dpreview.com"
    search_url: str = "https://www.dpreview.com/products/cameras/all?view=list"
    rate_limit_per_minute: int = 20
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 2.0

    # Browser
    headless: bool = True
    browser_timeout: int = 30000  # milliseconds
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Output
    output_dir: Path = Path("output")
    progress_file: Path = Path(".scrape_progress.json")

    # Date filtering
    after_date: str = "2023-03-01"  # Default to after existing database

    # Logging
    log_level: str = "INFO"
    verbose: bool = False

    model_config = SettingsConfigDict(
        env_prefix="DPREVIEW_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


# Global settings instance
settings = Settings()
