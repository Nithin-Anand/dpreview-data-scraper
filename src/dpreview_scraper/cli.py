"""Command-line interface."""

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from dpreview_scraper import __version__
from dpreview_scraper.config import settings
from dpreview_scraper.scraper.browser import BrowserManager
from dpreview_scraper.scraper.search import SearchScraper
from dpreview_scraper.scraper.product import ProductScraper
from dpreview_scraper.scraper.archive import ArchiveManager
from dpreview_scraper.storage.yaml_writer import YAMLWriter
from dpreview_scraper.storage.progress import ProgressTracker
from dpreview_scraper.utils.rate_limiter import RateLimiter
from dpreview_scraper.utils.logging import setup_logging, logger

app = typer.Typer(help="DPReview Camera Scraper - Extract camera specs from DPReview")
console = Console()


@app.command()
def scrape(
    output: Path = typer.Option(
        Path("output"),
        "--output",
        "-o",
        help="Output directory for YAML files",
    ),
    after: str = typer.Option(
        "2023-03-01",
        "--after",
        "-a",
        help="Only scrape cameras announced after this date (YYYY-MM-DD)",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of cameras to scrape",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    archive: bool = typer.Option(
        False,
        "--archive",
        help="Fetch Wayback Machine archive URLs",
    ),
    resume: bool = typer.Option(
        True,
        "--resume/--no-resume",
        help="Resume from previous progress",
    ),
):
    """Scrape camera data from DPReview."""
    setup_logging(verbose)

    console.print(f"[bold blue]DPReview Camera Scraper v{__version__}[/bold blue]")
    console.print(f"Output directory: {output}")
    console.print(f"Filtering cameras after: {after}")
    console.print()

    # Run async scraper
    asyncio.run(
        _run_scraper(
            output=output,
            after_date=after,
            limit=limit,
            headless=headless,
            fetch_archive=archive,
            resume=resume,
        )
    )


async def _run_scraper(
    output: Path,
    after_date: str,
    limit: Optional[int],
    headless: bool,
    fetch_archive: bool,
    resume: bool,
):
    """Async scraper implementation."""
    # Initialize components
    browser = BrowserManager(headless=headless)
    rate_limiter = RateLimiter(requests_per_minute=settings.rate_limit_per_minute)
    yaml_writer = YAMLWriter(output)
    progress_tracker = ProgressTracker(settings.progress_file)

    archive_manager = None  # Initialize here to avoid UnboundLocalError

    try:
        await browser.start()

        # Scrape search results
        console.print("[bold]Searching for cameras...[/bold]")
        search_scraper = SearchScraper(browser, rate_limiter, after_date=after_date)

        # Calculate max_pages based on limit to avoid unnecessary searching
        # Each page has ~50 cameras, so add buffer for filtering
        max_pages = None
        if limit:
            max_pages = (limit // 50) + 2  # +2 for buffer after date filtering
            logger.info(f"Limiting search to ~{max_pages} pages for {limit} cameras")

        search_results = await search_scraper.scrape_all_pages(max_pages=max_pages)

        if not search_results:
            console.print("[yellow]No cameras found![/yellow]")
            return

        console.print(f"[green]Found {len(search_results)} cameras[/green]")
        console.print()

        # Apply limit
        if limit:
            search_results = search_results[:limit]
            console.print(f"[yellow]Limited to {limit} cameras[/yellow]")

        # Filter out already completed if resuming
        if resume:
            remaining = progress_tracker.get_remaining(
                [r.product_code for r in search_results]
            )
            search_results = [r for r in search_results if r.product_code in remaining]

            if not search_results:
                console.print("[green]All cameras already scraped![/green]")
                stats = progress_tracker.get_stats()
                _print_stats(stats)
                return

            console.print(
                f"[yellow]Resuming: {len(search_results)} cameras remaining[/yellow]"
            )
            console.print()

        # Start progress tracking
        progress_tracker.start(len(search_results))

        # Initialize archive manager if needed
        if fetch_archive:
            archive_manager = ArchiveManager()

        # Scrape products
        product_scraper = ProductScraper(browser, rate_limiter)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Scraping cameras...", total=len(search_results))

            for search_result in search_results:
                try:
                    # Skip if already exists and not resuming
                    if yaml_writer.camera_exists(search_result.product_code):
                        logger.info(f"Skipping existing: {search_result.product_code}")
                        progress_tracker.mark_completed(search_result.product_code)
                        progress.advance(task)
                        continue

                    # Scrape product
                    camera = await product_scraper.scrape_product(search_result)

                    if not camera:
                        logger.warning(f"Failed to scrape: {search_result.product_code}")
                        progress_tracker.mark_failed(search_result.product_code)
                        progress.advance(task)
                        continue

                    # Fetch archive URL if requested
                    if archive_manager:
                        review_url = f"{settings.base_url}/reviews/{search_result.product_code}-review"
                        archive_url = await archive_manager.get_archive_url(review_url)
                        if archive_url:
                            camera.DPRReviewArchiveURL = archive_url

                    # Write YAML
                    yaml_writer.write_camera(camera)
                    progress_tracker.mark_completed(search_result.product_code)

                except Exception as e:
                    logger.error(f"Error scraping {search_result.product_code}: {e}")
                    progress_tracker.mark_failed(search_result.product_code)

                progress.advance(task)

        # Print final stats
        console.print()
        console.print("[bold green]Scraping complete![/bold green]")
        stats = progress_tracker.get_stats()
        _print_stats(stats)

    finally:
        await browser.stop()
        if archive_manager:
            await archive_manager.close()


@app.command()
def list_cameras(
    after: str = typer.Option(
        "2023-03-01",
        "--after",
        "-a",
        help="Only show cameras announced after this date",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number to list",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """List available cameras without full scrape."""
    setup_logging(verbose)

    console.print("[bold]Searching for cameras...[/bold]")

    asyncio.run(_list_cameras_async(after, limit, headless))


async def _list_cameras_async(after: str, limit: Optional[int], headless: bool):
    """Async implementation of list command."""
    browser = BrowserManager(headless=headless)
    rate_limiter = RateLimiter(requests_per_minute=settings.rate_limit_per_minute)

    try:
        await browser.start()

        search_scraper = SearchScraper(browser, rate_limiter, after_date=after)
        results = await search_scraper.scrape_all_pages()

        if limit:
            results = results[:limit]

        # Display results
        table = Table(title=f"Found {len(results)} Cameras")
        table.add_column("Product Code", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Announced", style="yellow")

        for result in results:
            table.add_row(
                result.product_code,
                result.name,
                result.announced or "Unknown",
            )

        console.print(table)

    finally:
        await browser.stop()


@app.command()
def validate(
    directory: Path = typer.Argument(
        ...,
        help="Directory containing YAML files to validate",
    ),
):
    """Validate YAML output files."""
    import yaml
    from dpreview_scraper.models.camera import Camera

    if not directory.exists():
        console.print(f"[red]Directory not found: {directory}[/red]")
        raise typer.Exit(1)

    yaml_files = list(directory.glob("*.yaml"))

    if not yaml_files:
        console.print(f"[yellow]No YAML files found in {directory}[/yellow]")
        return

    console.print(f"Validating {len(yaml_files)} files...")

    valid = 0
    invalid = 0

    for yaml_file in yaml_files:
        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)

            # Try to parse as Camera
            Camera(**data)
            valid += 1

        except Exception as e:
            console.print(f"[red]Invalid: {yaml_file.name} - {e}[/red]")
            invalid += 1

    console.print()
    console.print(f"[green]Valid: {valid}[/green]")
    console.print(f"[red]Invalid: {invalid}[/red]")


@app.command()
def dump_html(
    output_dir: Path = typer.Option(
        Path("tests/fixtures"),
        "--output",
        "-o",
        help="Directory to save HTML files",
    ),
    product_url: Optional[str] = typer.Option(
        None,
        "--product",
        "-p",
        help="Optional product page URL to fetch",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """Fetch and save HTML pages for selector analysis."""
    setup_logging(verbose)

    console.print("[bold]Fetching HTML from DPReview...[/bold]")

    asyncio.run(_dump_html_async(output_dir, product_url, headless))


async def _dump_html_async(output_dir: Path, product_url: Optional[str], headless: bool):
    """Async implementation of dump-html command."""
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    browser = BrowserManager(headless=headless)

    try:
        await browser.start()

        async with browser.new_page() as page:
            # Fetch camera list page
            console.print(f"Fetching camera list from {settings.search_url}...")
            await page.goto(settings.search_url, wait_until="networkidle")
            await asyncio.sleep(2)  # Extra wait for dynamic content

            camera_list_html = await page.content()
            camera_list_path = output_dir / "camera_list.html"
            camera_list_path.write_text(camera_list_html, encoding="utf-8")
            console.print(f"[green]✓ Saved: {camera_list_path}[/green]")

            # Fetch product page if URL provided, or use first camera found
            if product_url:
                target_url = product_url
            else:
                # Try to find first camera link
                console.print("Finding first camera link...")
                try:
                    # Look for product links (this is a placeholder selector - we'll update it)
                    first_link = await page.query_selector('a[href*="/products/"]')
                    if first_link:
                        href = await first_link.get_attribute('href')
                        if href:
                            target_url = f"{settings.base_url}{href}" if href.startswith('/') else href
                        else:
                            target_url = None
                    else:
                        target_url = None
                except Exception as e:
                    logger.warning(f"Could not find camera link: {e}")
                    target_url = None

            if target_url:
                console.print(f"Fetching product page from {target_url}...")
                await page.goto(target_url, wait_until="networkidle")
                await asyncio.sleep(2)  # Extra wait for dynamic content

                product_html = await page.content()
                product_path = output_dir / "product_sample.html"
                product_path.write_text(product_html, encoding="utf-8")
                console.print(f"[green]✓ Saved: {product_path}[/green]")
            else:
                console.print("[yellow]No product URL provided and couldn't find a camera link[/yellow]")

            console.print()
            console.print(f"[bold green]HTML files saved to: {output_dir}[/bold green]")

    finally:
        await browser.stop()


@app.command()
def clear_progress():
    """Clear scraping progress."""
    progress_tracker = ProgressTracker(settings.progress_file)
    progress_tracker.clear()
    console.print("[green]Progress cleared[/green]")


@app.command()
def version():
    """Show version information."""
    console.print(f"DPReview Camera Scraper v{__version__}")


def _print_stats(stats: dict):
    """Print progress statistics."""
    table = Table(title="Scraping Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Cameras", str(stats["total"]))
    table.add_row("Completed", str(stats["completed"]))
    table.add_row("Failed", str(stats["failed"]))
    table.add_row("Remaining", str(stats["remaining"]))
    table.add_row("Progress", f"{stats['progress_percent']}%")

    console.print(table)


if __name__ == "__main__":
    app()
