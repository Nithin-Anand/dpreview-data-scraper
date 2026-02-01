# Development Guide

## Current Status

The scraper implementation is **complete** but requires HTML selector adjustments before production use.

## Next Steps (Required Before First Run)

### 1. Update HTML Parsers with Actual Selectors

The parsers currently use template selectors that need adjustment based on DPReview's actual HTML structure.

#### Search Parser (`src/dpreview_scraper/parsers/search_parser.py`)

**What to do:**
1. Visit https://www.dpreview.com/products/cameras/all?view=list in a browser
2. Open Developer Tools (F12) and inspect the page structure
3. Identify the correct selectors for:
   - Product cards/containers
   - Product name elements
   - Product URLs/links
   - Product images
   - Announcement dates
   - Pagination elements

**Current template selectors to update:**
```python
# Line ~17: Product elements
product_elements = soup.select(".product-list .product")  # UPDATE THIS
product_elements = soup.select("[data-product-code]")     # OR THIS

# Line ~26: Product link
link = element.select_one("a[href*='/products/']")        # UPDATE THIS

# Line ~40: Product name
name_elem = element.select_one(".product-name, h3, h2, a[href*='/products/']")  # UPDATE

# Line ~44: Product image
img = element.select_one("img")                           # VERIFY THIS

# Line ~49: Announcement date
date_elem = element.select_one(".announced, .date, [data-announced]")  # UPDATE

# Line ~77: Pagination
pagination = soup.select_one(".pagination, .paging, nav[role='navigation']")  # UPDATE
```

#### Product Parser (`src/dpreview_scraper/parsers/product_parser.py`)

**What to do:**
1. Visit a sample product page (e.g., https://www.dpreview.com/products/fujifilm/slrs/fujifilm_xpro3)
2. Inspect the page structure
3. Identify selectors for:
   - Product name/title
   - Main product image
   - Short specs/key features list
   - Review score
   - Award badge
   - Specifications table
   - Review summary sections
   - Product photo gallery
   - Amazon ASIN links

**Current template selectors to update:**
```python
# Line ~34: Product name
selectors = ["h1.product-name", "h1.title", ".product-header h1", "h1"]  # UPDATE

# Line ~48: Product image
img = soup.select_one(".product-image img, .main-image img, .hero-image img")  # UPDATE

# Line ~60: Short specs
spec_elem = soup.select_one(".key-specs, .short-specs, .specs-summary")  # UPDATE

# Line ~74: Review score
score_elem = soup.select_one(".review-score, .score, [data-score]")  # UPDATE

# Line ~87: Award
award_elem = soup.select_one(".award, .badge, [data-award]")  # UPDATE

# Line ~102: Specs table
specs_section = soup.select_one(".specs-table, #specifications, .technical-specs")  # UPDATE

# Line ~240: Executive summary
summary_elem = soup.select_one(".executive-summary, .overview, .introduction")  # UPDATE

# Line ~244: Product photos
photo_gallery = soup.select_one(".product-gallery, .photo-gallery, .images")  # UPDATE

# Line ~254: Review summary
summary_section = soup.select_one(".review-summary, .verdict, .conclusion")  # UPDATE
```

### 2. Test with a Small Sample

**Recommended first run:**
```bash
# Run with visible browser and verbose logging to debug
uv run dpreview-scraper scrape --limit 1 --no-headless --verbose

# Or just list cameras first
uv run dpreview-scraper list-cameras --limit 5 --no-headless --verbose
```

**Watch for:**
- 403 errors (may need to adjust headers or add delays)
- Empty results (wrong selectors)
- Missing data fields (selectors not matching)
- JavaScript-rendered content (may need wait conditions)

### 3. Refine Spec Field Mapping

The `_normalize_spec_name()` function in `product_parser.py` (line ~173) maps DPReview's spec labels to our field names. You'll likely need to add more mappings based on actual labels found on the site.

**Example additions:**
```python
mapping = {
    # ... existing mappings ...
    "aperture priority": "AperturePriority",
    "shutter priority": "ShutterPriority",
    "video resolution": "Modes",
    # Add more as you discover them
}
```

### 4. Handle Edge Cases

Once basic scraping works, handle:
- Cameras with incomplete specs
- Different page layouts (some cameras may have different templates)
- Video mode parsing (complex multi-line format)
- List vs. single value fields
- Date format variations

## Development Workflow

### Running Tests
```bash
# Run with small limit first
uv run dpreview-scraper scrape --limit 3 --verbose

# Check output
ls -la output/

# Validate output
uv run dpreview-scraper validate ./output
```

### Debugging

1. **Enable visible browser:**
   ```bash
   uv run dpreview-scraper scrape --no-headless --verbose
   ```

2. **Save HTML for offline testing:**
   Add to browser.py or create a debug mode that saves page HTML to `tests/fixtures/`

3. **Check progress:**
   Progress is saved in `.scrape_progress.json` - you can inspect this file to see what's been completed

4. **Check logs:**
   Logs show which selectors are failing and where parsing issues occur

### Adding HTML Fixtures for Testing

Once you have working selectors, save sample HTML for testing:

```bash
# Create fixtures directory
mkdir -p tests/fixtures

# Manually save HTML files:
# - search_results_page1.html (from search page)
# - product_fujifilm_xpro3.html (from a product page)
```

Then create unit tests in `tests/unit/` to test parsers against fixtures.

## Known Limitations

1. **Spec field mapping incomplete** - Only common fields mapped, will need expansion
2. **Video modes parsing simplified** - Complex format may need special handling
3. **No retry on parser failures** - Currently just logs warnings
4. **Archive URLs** - Wayback Machine may not have all reviews archived

## Rate Limiting Guidelines

- **Default:** 20 requests/minute with 0.5-2s jitter
- **Conservative:** 10 requests/minute for initial testing
- **Aggressive:** 30 requests/minute (monitor for blocks)

Adjust in `config.py` or via environment variable:
```bash
export DPREVIEW_RATE_LIMIT_PER_MINUTE=10
```

## Troubleshooting Common Issues

### 403 Forbidden Errors
- Site is blocking requests
- Try reducing rate limit
- Check browser headers in `scraper/browser.py`
- Add random delays between requests

### No Products Found
- Wrong selectors in `search_parser.py`
- Page uses JavaScript rendering (add longer waits)
- Pagination not working (check pagination selectors)

### Missing Spec Data
- Selectors don't match actual page structure
- Spec labels don't match mapping in `_normalize_spec_name()`
- DPReview uses different field names than expected

### Playwright Issues
```bash
# Reinstall browsers
uv run playwright install chromium

# Install system dependencies (Linux)
uv run playwright install-deps
```

## Future Enhancements

- [ ] Add unit tests with HTML fixtures
- [ ] Improve video mode parsing
- [ ] Add spec completeness scoring
- [ ] Support for review text extraction
- [ ] Image downloading
- [ ] Database storage option (SQLite/PostgreSQL)
- [ ] API mode (serve data via FastAPI)
- [ ] Incremental updates (only scrape new cameras)
- [ ] Comparison with existing database for diff detection

## Contributing

When adding features:
1. Update parsers to handle new fields
2. Update models if schema changes
3. Add tests for new functionality
4. Update documentation
5. Test with `--limit 3` before full runs
