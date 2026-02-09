# Development Guide

## Selector Maintenance

DPReview's HTML structure can change over time. When selectors break, you'll see warnings in verbose output like `No product elements found` or `UNMAPPED LABEL: ...`.

### How to Update Selectors

1. **Capture current HTML:**
   ```bash
   uv run dpreview-scraper dump-html
   ```

2. **Inspect the saved HTML** to identify correct CSS selectors

3. **Update the relevant parser file:**
   - Search results: `parsers/search_parser.py`
   - Product metadata: `parsers/metadata_parser.py`
   - Specifications: `parsers/specs_parser.py`
   - Review content: `parsers/review_parser.py`

4. **Update test fixtures** if the HTML structure changed significantly

5. **Run tests** to verify: `uv run python -m pytest -v`

### Adding Spec Field Mappings

When you see `UNMAPPED LABEL` in verbose output, add the mapping to `SPEC_LABEL_MAPPING` in `parsers/specs_parser.py`:

```python
SPEC_LABEL_MAPPING = {
    # ...existing mappings...
    "new label name": "ExistingFieldName",
}
```

If the field doesn't exist yet, add it to `models/specs.py` first.

## Debugging

```bash
# Visible browser + debug logging
uv run dpreview-scraper scrape --no-headless --verbose --limit 1

# Just list cameras (no scraping)
uv run dpreview-scraper list-cameras --limit 5 --verbose

# Check progress file
cat .scrape_progress.json | python -m json.tool
```

## Rate Limiting

| Setting | Requests/min | Use case |
|---------|-------------|----------|
| Conservative | 10 | Initial testing, debugging |
| Default | 20 | Normal scraping |
| Aggressive | 30 | Only if you're confident there are no blocks |

```bash
export DPREVIEW_RATE_LIMIT_PER_MINUTE=10
```

## Known Limitations

- Spec field mapping covers common fields; niche specs may be unmapped
- Video mode strings have a complex format that's simplified during parsing
- Archive URLs depend on Wayback Machine availability
- Cloudflare protection can occasionally block review page access (falls back to basic specs)

## Future Ideas

- Spec completeness scoring per camera
- Image downloading and local storage
- Database backend (SQLite/PostgreSQL) as alternative to YAML
- Incremental updates (detect and scrape only new cameras)
- Diff detection against existing Open Camera Database
