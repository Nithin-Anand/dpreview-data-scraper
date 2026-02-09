# DPReview Camera Data Scraper

[![CI](https://github.com/YOUR_USERNAME/dpreview-data-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/dpreview-data-scraper/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Python scraper that extracts camera specifications and review data from [DPReview](https://www.dpreview.com), outputting structured YAML files.

## Why This Exists

DPReview is the most comprehensive camera review database on the web, but there's no public API for accessing its structured data. The [Open Camera Database](https://github.com/open-camera-database) has curated camera data through March 2023 but stopped receiving updates.

This tool fills the gap by scraping DPReview product pages and producing YAML files in the same schema the open database uses, covering cameras announced from March 2023 onward.

## Features

- **Automated scraping** of DPReview's camera product database
- **Comprehensive data extraction** -- specs, reviews, product photos, Amazon ASINs
- **Wayback Machine integration** for archiving review URLs
- **Resume capability** with progress tracking (interrupted scrapes pick up where they left off)
- **Rate limiting** with token-bucket algorithm and human-like jitter
- **YAML output** matching the Open Camera Database schema

## Installation

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
git clone https://github.com/YOUR_USERNAME/dpreview-data-scraper.git
cd dpreview-data-scraper

uv sync
uv run playwright install chromium
```

## Quick Start

```bash
# Scrape cameras announced after March 2023 (default)
uv run dpreview-scraper scrape

# List available cameras without scraping
uv run dpreview-scraper list-cameras

# Scrape with options
uv run dpreview-scraper scrape --output ./data --after 2024-01-01 --limit 10

# Show all commands
uv run dpreview-scraper --help
```

## Commands

### `scrape`

The main scraping command:

```bash
uv run dpreview-scraper scrape [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output, -o` | `output/` | Output directory for YAML files |
| `--after, -a` | `2023-03-01` | Only scrape cameras announced after this date |
| `--limit, -l` | unlimited | Maximum number of cameras to scrape |
| `--headless/--no-headless` | headless | Browser visibility (use `--no-headless` for debugging) |
| `--verbose, -v` | off | Enable debug logging |
| `--archive/--no-archive` | enabled | Fetch Wayback Machine archive URLs |
| `--resume/--no-resume` | enabled | Resume from previous progress |

### `list-cameras`

Preview available cameras without performing a full scrape.

### `backfill-archives`

Add or update Wayback Machine archive URLs to existing YAML files without re-scraping:

```bash
# Lookup existing archives
uv run dpreview-scraper backfill-archives output/

# Also create new archives for cameras that don't have them
uv run dpreview-scraper backfill-archives output/ --create-if-missing
```

### `validate`

Validate YAML output files for schema compliance.

### `clear-progress`

Clear saved scraping progress to start fresh.

## Output Format

Each camera produces a YAML file like this (see `sample_data/` for complete examples):

```yaml
DPRReviewArchiveURL: https://web.archive.org/web/...
ProductCode: sony_fx30
Award: ""
ImageURL: /files/p/products/sony_fx30/04ab576b...png
Name: Sony FX30
ShortSpecs:
    - 26 megapixels
    - 3″ screen
    - APS-C sensor
ReviewScore: 0
URL: /products/sony/slrs/sony_fx30
ReviewData:
    ExecutiveSummary: 'The compact, very accessible FX30...'
    ProductPhotos:
        - /files/p/products/sony_fx30/shots/184e70fa...png
    ReviewSummary: null
    ASIN:
        - B0BKLQFFSF
Specs:
    Announced: Sep 28, 2022
    AperturePriority: "Yes"
    Autofocus:
        - Phase Detect
        - Multi-area
        - Tracking
    BodyType: SLR-style mirrorless
    SensorType: BSI-CMOS
    # ... 70+ additional spec fields
```

## Configuration

All settings can be controlled via environment variables (prefix `DPREVIEW_`) or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DPREVIEW_RATE_LIMIT_PER_MINUTE` | `20` | Max requests per minute |
| `DPREVIEW_BROWSER_TIMEOUT` | `30000` | Browser navigation timeout (ms) |
| `DPREVIEW_OUTPUT_DIR` | `./output` | Default output directory |
| `DPREVIEW_LOG_LEVEL` | `INFO` | Logging level |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development setup and guidelines.

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run python -m pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

### Project Structure

```
src/dpreview_scraper/
├── cli.py               # CLI commands (typer)
├── config.py            # Settings and environment variables
├── models/              # Pydantic data models (camera, review, specs)
├── scraper/             # Browser automation
│   ├── browser.py       # Playwright browser management
│   ├── search.py        # Search page scraper
│   ├── product.py       # Product page scraper
│   ├── stealth.py       # Anti-detection & Cloudflare handling
│   └── archive.py       # Wayback Machine integration
├── parsers/             # HTML parsing (no browser dependency)
│   ├── product_parser.py  # Orchestrator
│   ├── metadata_parser.py # Name, image, award extraction
│   ├── specs_parser.py    # Technical specifications
│   ├── review_parser.py   # Review data extraction
│   ├── search_parser.py   # Search result parsing
│   └── parse_utils.py     # Shared regex and text utilities
├── storage/             # Output handling
│   ├── yaml_writer.py   # YAML file output
│   └── progress.py      # Resume tracking
└── utils/
    ├── logging.py       # Logging setup
    └── rate_limiter.py  # Token bucket rate limiter
```

## Troubleshooting

**403 Errors:** DPReview has anti-bot protection. The scraper uses Playwright with stealth mode to handle this. If issues persist, reduce rate limit: `DPREVIEW_RATE_LIMIT_PER_MINUTE=10`

**Timeout Errors:** Increase browser timeout: `DPREVIEW_BROWSER_TIMEOUT=60000`. Use `--no-headless` to observe browser behavior.

**Missing Data:** Some cameras have incomplete specs on DPReview. All fields default to empty strings. Use `--verbose` to see parsing warnings.

**Playwright Issues:** Ensure browser is installed: `uv run playwright install chromium`. On Linux you may also need: `uv run playwright install-deps`.

## License

MIT License -- see [LICENSE](LICENSE) for details.

## Disclaimer

This tool is for personal and educational use. It scrapes publicly available data from DPReview. Please use reasonable rate limiting and do not overload their servers. The authors are not responsible for misuse.

DPReview content is the property of its respective owners. This tool does not redistribute copyrighted content -- it extracts structured metadata (specifications, scores, URLs) for personal database use.
