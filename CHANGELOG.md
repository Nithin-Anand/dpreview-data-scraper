# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Unit test suite (80 tests) covering parsers, models, YAML writer, progress tracker, and rate limiter
- GitHub Actions CI workflow (lint + test)
- CONTRIBUTING.md with development setup and contribution guidelines
- GitHub issue templates (bug report, feature request) and PR template
- CHANGELOG.md

### Changed
- Split `product_parser.py` (1010 lines) into focused modules:
  - `metadata_parser.py` -- name, image, award, announced date
  - `specs_parser.py` -- technical specifications and field mapping
  - `review_parser.py` -- executive summary, review scores, pros/cons
  - `parse_utils.py` -- shared regex and text normalization
  - `product_parser.py` -- slim orchestrator
- Extracted Cloudflare/stealth handling from `ProductScraper` into `scraper/stealth.py`
- Improved README with motivation section, inline YAML example, configuration table, and clearer disclaimer

## [0.1.0] - 2026-02-07

### Added
- Initial scraper implementation with Playwright browser automation
- Search page scraper with pagination and date filtering
- Product page scraper with overview, specs, and review page support
- Cloudflare challenge bypass with human-like behavior simulation
- Wayback Machine integration for archiving review URLs
- `backfill-archives` command for adding archives to existing YAML files
- Resume capability with JSON-based progress tracking
- Token bucket rate limiter with jitter
- YAML output matching Open Camera Database schema
- CLI with `scrape`, `list-cameras`, `validate`, `backfill-archives`, `clear-progress`, `dump-html` commands
- Pydantic models for camera data, review data, and 70+ spec fields
- Custom YAML dumper with proper string quoting and formatting
