# DPReview Camera Data Scraper

A Python-based web scraper for extracting camera specifications and review data from [DPReview](https://www.dpreview.com). Outputs structured YAML files for contribution to open camera databases.

## Features

- **Automated scraping** of DPReview's camera product database
- **Comprehensive data extraction** including specs, reviews, and product photos
- **Wayback Machine integration** for archiving review URLs
- **Resume capability** with progress tracking
- **Rate limiting** and anti-detection measures
- **YAML output** matching standardized camera database schema

## Installation

Requires Python 3.12+. This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone <repository-url>
cd dpreview-data-scraper

# Install dependencies using uv
uv sync

# Install Playwright browser
uv run playwright install chromium
```

> **⚠️ Important:** Before first use, you must update HTML selectors in the parser files to match DPReview's actual site structure. See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions.

## Quick Start

```bash
# Scrape cameras announced after March 2023
uv run dpreview-scraper scrape

# List available cameras without full scrape
uv run dpreview-scraper list-cameras

# Scrape with custom options
uv run dpreview-scraper scrape --output ./data --after 2024-01-01 --limit 10

# Show help
uv run dpreview-scraper --help
```

## Usage

### Scrape Command

The main command to scrape camera data:

```bash
uv run dpreview-scraper scrape [OPTIONS]
```

**Options:**

- `--output, -o PATH` - Output directory for YAML files (default: `output/`)
- `--after, -a DATE` - Only scrape cameras announced after this date (default: `2023-03-01`)
- `--limit, -l N` - Maximum number of cameras to scrape
- `--headless/--no-headless` - Run browser in headless mode (default: headless)
- `--verbose, -v` - Enable verbose logging
- `--archive/--no-archive` - Fetch Wayback Machine archive URLs (default: enabled)
- `--resume/--no-resume` - Resume from previous progress (default: resume)

**Examples:**

```bash
# Basic scrape with defaults
uv run dpreview-scraper scrape

# Scrape with visible browser for debugging
uv run dpreview-scraper scrape --no-headless --verbose

# Scrape recent cameras without archive URLs (faster)
uv run dpreview-scraper scrape --after 2024-06-01 --no-archive

# Scrape limited number for testing
uv run dpreview-scraper scrape --limit 5
```

### List Cameras Command

Preview available cameras without full scraping:

```bash
uv run dpreview-scraper list-cameras [OPTIONS]
```

**Options:**

- `--after, -a DATE` - Filter by announcement date
- `--limit, -l N` - Maximum number to list
- `--headless/--no-headless` - Browser mode
- `--verbose, -v` - Verbose logging

### Backfill Archives Command

Add or update Wayback Machine archive URLs to existing YAML files without re-scraping:

```bash
uv run dpreview-scraper backfill-archives <directory> [OPTIONS]
```

**Options:**

- `--create-if-missing` - Create new Wayback Machine archives if none exist (slower, but ensures all cameras have archives)
- `--verbose, -v` - Verbose logging

**Examples:**

```bash
# Add archive URLs to existing YAML files (lookup only)
uv run dpreview-scraper backfill-archives output/

# Create new archives for cameras that don't have them yet
uv run dpreview-scraper backfill-archives output/ --create-if-missing

# Verbose mode to see progress
uv run dpreview-scraper backfill-archives output/ --verbose
```

**Use cases:**

- You scraped cameras with `--no-archive` and want to add archives later
- Archive URLs failed during initial scrape
- You want to update existing YAML files without re-scraping camera data

**Performance:**
- Lookup only: ~2-3 minutes for 85 cameras
- With `--create-if-missing`: ~3-6 minutes first run, ~2-3 minutes on re-runs (archives already exist)

### Validate Command

Validate YAML output files:

```bash
uv run dpreview-scraper validate <directory>
```

### Clear Progress

Clear saved scraping progress:

```bash
uv run dpreview-scraper clear-progress
```

## Output Format

The scraper generates YAML files following this structure (see `sample_data/fujifilm_xpro3.yaml` for a complete example):

```yaml
DPRReviewArchiveURL: https://web.archive.org/web/...
ProductCode: fujifilm_xpro3
Award: silver
ImageURL: /files/p/products/fujifilm_xpro3/...
Name: Fujifilm X-Pro3
ShortSpecs:
    - 26 megapixels
    - 3″ screen
    - APS-C sensor
ReviewScore: 85
URL: /products/fujifilm/slrs/fujifilm_xpro3
ReviewData:
    ExecutiveSummary: "..."
    ProductPhotos: [...]
    ReviewSummary:
        GoodFor: "..."
        NotSoGoodFor: "..."
        Conclusion: "..."
    ASIN: [...]
Specs:
    Announced: Oct 23, 2019
    BodyType: Rangefinder-style mirrorless
    SensorType: BSI-CMOS
    # ... 70+ additional spec fields
```

## Configuration

Environment variables can be set via a `.env` file or shell exports. All variables use the `DPREVIEW_` prefix:

```bash
# Rate limiting (requests per minute)
DPREVIEW_RATE_LIMIT_PER_MINUTE=20

# Browser timeout (milliseconds)
DPREVIEW_BROWSER_TIMEOUT=30000

# Output directory
DPREVIEW_OUTPUT_DIR=./output

# Logging
DPREVIEW_LOG_LEVEL=INFO
```

## Development

> **📖 See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions, next steps, and troubleshooting.**

### Project Structure

```
dpreview-data-scraper/
├── src/dpreview_scraper/
│   ├── models/          # Pydantic data models
│   ├── scraper/         # Browser automation & scrapers
│   ├── parsers/         # HTML parsing
│   ├── storage/         # YAML output & progress tracking
│   └── utils/           # Rate limiting, logging
├── sample_data/         # Example YAML output
└── tests/               # Test suite
```

### Running Tests

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=dpreview_scraper
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src/
```

## Technical Details

### Anti-Detection Measures

- Realistic browser headers and viewport
- JavaScript-based navigator.webdriver masking
- Token bucket rate limiting with jitter
- Human-like delays between requests

### Resumability

Progress is tracked in `.scrape_progress.json`. If scraping is interrupted:

1. Run the same command again
2. Already scraped cameras are automatically skipped
3. Scraping continues from where it left off

Use `--no-resume` to start fresh.

### Wayback Machine Integration

Archive URLs are **enabled by default** during scraping. The scraper fetches existing Wayback Machine snapshots for review pages.

**During scraping:**
- `--archive` (default) - Fetch existing archive URLs
- `--no-archive` - Skip archive fetching (faster)

**After scraping:**
- Use `backfill-archives` command to add/update archive URLs without re-scraping
- Use `--create-if-missing` flag to create new archives for cameras that don't have them

**Why archive URLs?**
- Preserves review content in case DPReview updates or removes pages
- Provides a permanent, timestamped snapshot of reviews
- Useful for historical reference and data integrity

## Troubleshooting

**403 Errors:**
- DPReview has anti-bot protection. The scraper uses browser automation to handle this.
- If issues persist, reduce rate limit: `DPREVIEW_RATE_LIMIT_PER_MINUTE=10`

**Timeout Errors:**
- Increase browser timeout: `DPREVIEW_BROWSER_TIMEOUT=60000`
- Use `--no-headless` to observe browser behavior

**Missing Data:**
- Some cameras may have incomplete specifications on DPReview
- All spec fields default to empty strings if not found
- Check logs with `--verbose` to see parsing warnings

**Playwright Issues:**
- Ensure Playwright is installed: `uv run playwright install chromium`
- On some systems you may need: `uv run playwright install-deps`

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code passes linting and formatting
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Data sourced from [DPReview](https://www.dpreview.com)
- Built for contribution to open camera databases
- Uses [Playwright](https://playwright.dev/) for browser automation

## Disclaimer

This tool is for educational purposes and personal use. Please respect DPReview's terms of service and robots.txt. Use reasonable rate limiting and do not overload their servers.
