# Contributing to DPReview Data Scraper

Thanks for your interest in contributing! This guide covers how to set up the project, run tests, and submit changes.

## Development Setup

```bash
# Clone and enter the repo
git clone <repository-url>
cd dpreview-data-scraper

# Install all dependencies (including dev tools)
uv sync --dev

# Install Playwright browser
uv run playwright install chromium
```

## Running Tests

```bash
# Run the full test suite
uv run python -m pytest

# Run with verbose output
uv run python -m pytest -v

# Run a specific test file
uv run python -m pytest tests/test_search_parser.py

# Run with coverage
uv run python -m pytest --cov=dpreview_scraper
```

## Code Quality

Before submitting a PR, ensure your changes pass lint and formatting checks:

```bash
# Lint
uv run ruff check .

# Auto-fix lint issues
uv run ruff check . --fix

# Format
uv run ruff format .

# Check formatting without modifying
uv run ruff format --check .
```

## Project Structure

```
src/dpreview_scraper/
├── cli.py               # CLI commands (typer)
├── config.py            # Settings and environment variables
├── models/              # Pydantic data models
│   ├── camera.py        # Camera, SearchResult
│   ├── review.py        # ReviewData, ReviewSummary
│   └── specs.py         # CameraSpecs (70+ fields)
├── scraper/             # Browser automation
│   ├── browser.py       # Playwright browser management
│   ├── search.py        # Search page scraper
│   ├── product.py       # Product page scraper
│   ├── stealth.py       # Anti-detection & Cloudflare handling
│   └── archive.py       # Wayback Machine integration
├── parsers/             # HTML parsing (no browser dependency)
│   ├── search_parser.py # Search result parsing
│   └── product_parser.py# Product page parsing
├── storage/             # Output handling
│   ├── yaml_writer.py   # YAML file output
│   └── progress.py      # Resume tracking
└── utils/
    ├── logging.py       # Logging setup
    └── rate_limiter.py  # Token bucket rate limiter
```

## Common Contribution Types

### Adding or Fixing Spec Field Mappings

The spec field mapping in `parsers/product_parser.py` (`_normalize_spec_name`) maps HTML labels to model fields. To add a new mapping:

1. Run the scraper with `--verbose` to see unmapped labels:
   ```
   UNMAPPED LABEL: 'Some New Label' = 'value'
   ```
2. Add the label mapping to `_normalize_spec_name()` in `parsers/product_parser.py`
3. If the field doesn't exist in the model, add it to `models/specs.py`
4. Add a test for the new mapping in `tests/test_product_parser.py`

### Updating HTML Selectors

When DPReview's HTML structure changes, selectors may break. To update them:

1. Use `uv run dpreview-scraper dump-html` to save current HTML pages
2. Inspect the HTML to identify new selectors
3. Update the relevant parser file
4. Verify with the test fixtures - you may need to update fixtures too

### Adding New Test Fixtures

Test fixtures are real HTML pages saved in `tests/fixtures*/`. To capture new ones:

```bash
# Save current HTML for inspection
uv run dpreview-scraper dump-html
```

Copy the relevant files into a new `tests/fixtures_<name>/` directory. HTML fixtures are gitignored by default - update `.gitignore` if you want to commit them.

## Submitting Changes

1. Fork the repo and create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Ensure tests pass and lint is clean
4. Submit a pull request with a description of what changed and why

## Guidelines

- Keep changes focused - one feature or fix per PR
- Add tests for new functionality
- Don't modify scraped output files (`output/`) in PRs
- Be respectful of DPReview's servers - don't reduce rate limits below defaults
