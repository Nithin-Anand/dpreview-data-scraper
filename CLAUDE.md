# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based web scraper for extracting camera review data from DPReview's product search page. The scraper retrieves detailed camera specifications, review scores, product photos, and other metadata, outputting structured YAML files for contribution to an open camera database (which currently only has data through March 2023).

**Target URL:** https://www.dpreview.com/products/cameras/all?view=list (paginated results)

**Note:** DPReview returns 403 errors for simple HTTP requests, so the scraper will need to handle anti-bot measures (e.g., using browser automation, proper headers, rate limiting).

## Project Setup

**Python Version:** 3.12 (managed via `.python-version`)

**Dependency Management:** Uses `uv` for Python package and version management.

**Environment Setup:**
```bash
# Install dependencies using uv
uv sync

# Or add new dependencies
uv add <package-name>

# Run commands in the uv environment
uv run python main.py
```

## Data Structure

### Output Format

The scraper generates YAML files (see `sample_data/fujifilm_xpro3.yaml`) with the following structure:

- **Top-level metadata:**
  - `DPRReviewArchiveURL`: Wayback Machine URL of the original review
  - `ProductCode`: Unique identifier (e.g., `fujifilm_xpro3`)
  - `Award`: Review award tier (e.g., `silver`)
  - `ImageURL`: Product thumbnail path
  - `Name`: Human-readable camera name
  - `ShortSpecs`: Array of key specs (e.g., megapixels, screen size, sensor type)
  - `ReviewScore`: Numerical score (0-100)
  - `URL`: DPReview product page path

- **ReviewData section:**
  - `ExecutiveSummary`: Comprehensive overview of camera features
  - `ProductPhotos`: Array of product image URLs
  - `ReviewSummary`: Contains `GoodFor`, `NotSoGoodFor`, and `Conclusion` fields
  - `ASIN`: Array of Amazon product identifiers

- **Specs section:** Extensive technical specifications including:
  - Physical attributes (dimensions, weight, body material)
  - Sensor details (type, size, megapixels)
  - Autofocus system
  - Video capabilities with resolution/framerate/bitrate arrays
  - Connectivity (USB, wireless, ports)
  - Display specifications
  - Battery and storage information

### Key Data Patterns

1. **Video Modes**: Structured as multi-line strings with format: `resolution @ framerate / bitrate, container, codec, audio`
2. **Autofocus**: Arrays of capabilities (contrast/phase detect, tracking modes)
3. **ISO Values**: Ranges with optional boost extensions (e.g., `Auto, 160-12800 (expands to 80-51200)`)
4. **File Paths**: Relative paths starting with `/files/p/products/{product_code}/`

## Development Commands

**Run the scraper:**
```bash
# Scrape cameras (archive URLs enabled by default)
uv run dpreview-scraper scrape

# Scrape with options
uv run dpreview-scraper scrape --after 2024-01-01 --limit 10 --no-archive

# Backfill archive URLs to existing YAML files
uv run dpreview-scraper backfill-archives output/ --create-if-missing

# List available cameras
uv run dpreview-scraper list-cameras

# Validate YAML output
uv run dpreview-scraper validate output/
```

**Add dependencies:**
```bash
uv add beautifulsoup4 requests playwright  # Example
```

**Linting/Formatting:**
```bash
uv run ruff check .
uv run ruff format .
```

**Testing:**
```bash
uv run pytest
```

## Architecture Notes

- **Primary data source:** DPReview product search page (https://www.dpreview.com/products/cameras/all?view=list)
  - Uses Playwright for browser automation to handle anti-bot protection
  - Paginated search results with filtering by announcement date
  - Rate-limited requests with realistic headers and delays

- **Archive functionality:**
  - Archive URLs are **enabled by default** during scraping
  - Archives are fetched from Wayback Machine (not created by default for performance)
  - `backfill-archives` command can add/update archives to existing YAML files without re-scraping
  - Review URLs are extracted from product pages and stored internally for accurate archive lookup

- **Target date range:** Focus on cameras added after March 2023 (to complement existing open database)

- **Output:** YAML files matching the structure in `sample_data/`

- **Key components:**
  - `SearchScraper`: Extracts camera list from paginated search results
  - `ProductScraper`: Scrapes individual product and review pages for detailed specs
  - `ArchiveManager`: Handles Wayback Machine API integration
  - `YAMLWriter`: Outputs normalized YAML matching database schema
  - `ProgressTracker`: Enables resumable scraping after interruptions
