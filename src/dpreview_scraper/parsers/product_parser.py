"""Parse DPReview product pages.

This module orchestrates parsing of product overview, specs, and review pages
by delegating to focused submodules:
- metadata_parser: name, image, award, announced date
- specs_parser: technical specifications and field mapping
- review_parser: executive summary, review scores, pros/cons
- parse_utils: shared regex patterns and text normalization
"""

from typing import List, Optional

from bs4 import BeautifulSoup

from dpreview_scraper.models.camera import Camera
from dpreview_scraper.parsers.metadata_parser import (
    extract_announced,
    extract_award,
    extract_image_url,
    extract_name,
    extract_review_preview,
    extract_short_specs,
)
from dpreview_scraper.parsers.parse_utils import (
    extract_clean_url_from_style,
    normalize_whitespace,
)
from dpreview_scraper.parsers.review_parser import extract_review_data
from dpreview_scraper.parsers.specs_parser import (
    extract_full_specs,
    extract_review_specs,
    merge_specs,
    normalize_spec_name,
    parse_list_value,
)
from dpreview_scraper.utils.logging import logger

# Re-export for backward compatibility with existing tests and imports
_extract_clean_url_from_style = extract_clean_url_from_style
_extract_name = extract_name
_normalize_spec_name = normalize_spec_name
_normalize_whitespace = normalize_whitespace
_parse_list_value = parse_list_value


def parse_product_page(
    overview_html: str,
    specs_html: str,
    review_html: Optional[str],
    review_specs_html: Optional[str],
    product_code: str,
    url: str,
    short_specs: Optional[List[str]] = None,
) -> Camera:
    """Parse complete product page from multiple HTML sources.

    Args:
        overview_html: Product overview page HTML
        specs_html: Product specifications page HTML
        review_html: Product review page HTML (optional)
        review_specs_html: Review specs page HTML (optional, more comprehensive)
        product_code: Product code
        url: Product URL
        short_specs: Short specs from search results (optional)

    Returns:
        Camera object with all data
    """
    overview_soup = BeautifulSoup(overview_html, "lxml")
    specs_soup = BeautifulSoup(specs_html, "lxml")
    review_soup = BeautifulSoup(review_html, "lxml") if review_html else None
    review_specs_soup = BeautifulSoup(review_specs_html, "lxml") if review_specs_html else None

    # Extract top-level metadata from overview page
    name = extract_name(overview_soup)
    image_url = extract_image_url(overview_soup)
    if short_specs is None:
        short_specs = extract_short_specs(overview_soup)
    award = extract_award(overview_soup)

    # Extract specs: prioritize review specs (more comprehensive), fallback to regular specs
    if review_specs_soup:
        logger.debug("Using review specs page (more comprehensive)")
        specs = extract_review_specs(review_specs_soup)
        regular_specs = extract_full_specs(specs_soup)
        specs = merge_specs(specs, regular_specs)
    else:
        specs = extract_full_specs(specs_soup)

    # Extract announced date from overview page
    announced = extract_announced(overview_soup)
    if announced and not specs.Announced:
        specs.Announced = announced

    # Extract review data from overview and review pages
    review_data, review_score = extract_review_data(overview_soup, review_soup)

    # Extract ReviewPreview if not already in specs
    if not specs.ReviewPreview and review_score > 0:
        review_preview = extract_review_preview(overview_soup, review_score, award)
        if review_preview:
            specs.ReviewPreview = review_preview

    camera = Camera(
        ProductCode=product_code,
        Name=name,
        URL=url,
        ImageURL=image_url,
        ShortSpecs=short_specs,
        ReviewScore=review_score,
        Award=award,
        ReviewData=review_data,
        Specs=specs,
    )

    logger.debug(f"Parsed product page for {product_code}")
    return camera
