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
uv run python main.py
```

**Add dependencies:**
```bash
uv add beautifulsoup4 requests playwright  # Example
```

**Linting/Formatting:** (Add when tools are configured)
```bash
uv run ruff check .
uv run ruff format .
```

**Testing:** (Add when tests are implemented)
```bash
uv run pytest
```

## Architecture Notes

- The project is currently in early development with a skeleton `main.py`
- **Primary data source:** DPReview product search page (https://www.dpreview.com/products/cameras/all?view=list)
  - Paginated results - scraper needs to handle pagination
  - Site has anti-bot protection (403 errors on simple requests)
  - Will likely need browser automation (Playwright/Selenium) or sophisticated headers
- **Secondary requirement:** Archive URLs via Wayback Machine (stored in `DPRReviewArchiveURL` field)
- **Target date range:** Focus on cameras added after March 2023 (to complement existing open database)
- **Output:** YAML files matching the structure in `sample_data/`
- The scraper will need to:
  1. Navigate paginated search results
  2. Extract product URLs and metadata from search results
  3. Visit individual product/review pages for detailed specs
  4. Find or create Wayback Machine archive URLs for reviews
  5. Normalize data to match the expected YAML schema
