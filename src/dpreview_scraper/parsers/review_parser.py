"""Extract review data from overview and review pages."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from dpreview_scraper.models.review import ReviewData, ReviewSummary
from dpreview_scraper.parsers.parse_utils import extract_clean_url_from_style
from dpreview_scraper.utils.logging import logger


def _extract_overview_summary(soup: BeautifulSoup) -> str:
    """Extract summary/description from the overview page's description tab."""
    selectors = [
        "div.productOverviewPage div.section p",
        "div#descriptionTab div.productBody",
        "div#description div.productBody",
        "div.descriptionTab div.productBody",
        "div.productDescription div.productBody",
        "div.productDescription",
        "div.product-description",
        "div.productBody",
        "div#productBody",
        "div.leftColumn div.description p",
        "div.mainContent p.intro",
        "div.pressRelease",
        "div.announcement",
    ]

    blog_patterns = [
        r'\bthis month\b',
        r'\bchallenge\b',
        r'\bshare your\b',
        r'\bphoto adventures\b',
    ]

    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(separator=' ', strip=True)
            logger.debug(f"Selector '{selector}' matched element with {len(text)} chars")
            if text and len(text) > 100:
                text_lower = text.lower()
                if any(re.search(pattern, text_lower) for pattern in blog_patterns):
                    logger.debug(f"Skipping blog-like content from selector: {selector}")
                    continue

                logger.debug(f"Found executive summary from overview page with selector: {selector}")
                return text
            elif text:
                logger.debug(f"Text too short ({len(text)} chars): {text[:50]}...")
        else:
            logger.debug(f"Selector '{selector}' found no match")

    logger.warning("No executive summary found with any selector")
    return ""


def _parse_review_page(soup: BeautifulSoup) -> tuple[str, ReviewSummary, int]:
    """Parse review page content.

    Returns:
        Tuple of (executive_summary, review_summary, review_score)
    """
    executive_summary = ""
    good_for = ""
    not_so_good_for = ""
    conclusion = ""
    review_score = 0

    summary_selectors = [
        "div.mainContent div.article-intro",
        "div.content div.article-intro",
        "article div.article-intro",
        "div.reviewIntro",
        "div.review-intro",
        "div.mainContent div.articleBody p:first-of-type",
        "div.content div.articleBody p:first-of-type",
        "article div.articleBody p:first-of-type",
        "div.productDescription",
        "div.product-description",
    ]

    blog_patterns = [
        r'\bthis month\b',
        r'\bchallenge\b',
        r'\bshare your\b',
        r'\bphoto adventures\b',
    ]

    for selector in summary_selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(strip=True)
            if text and len(text) > 50:
                text_lower = text.lower()
                if any(re.search(pattern, text_lower) for pattern in blog_patterns):
                    logger.debug(f"Skipping blog-like content from selector: {selector}")
                    continue
                executive_summary = text
                logger.debug(f"Found executive summary with selector: {selector}")
                break

    score_selectors = [
        "span.overallScore",
        "span.score",
        "div.score",
        "[data-score]",
    ]

    for selector in score_selectors:
        elem = soup.select_one(selector)
        if elem:
            score_text = elem.get_text(strip=True)
            data_score = elem.get("data-score")
            score_value = data_score or score_text
            if score_value:
                try:
                    score_match = re.search(r"(\d+)", score_value)
                    if score_match:
                        review_score = int(score_match.group(1))
                        logger.debug(f"Found review score: {review_score} with selector: {selector}")
                        break
                except (ValueError, AttributeError):
                    continue

    good_for_elem = soup.select_one("tr.suitability.goodFor div.text")
    if good_for_elem:
        good_for = good_for_elem.get_text(strip=True)

    not_good_elem = soup.select_one("tr.suitability.notGoodFor div.text")
    if not_good_elem:
        not_so_good_for = not_good_elem.get_text(strip=True)

    conclusion_elem = soup.select_one("tr.summary div.summary")
    if conclusion_elem:
        conclusion = conclusion_elem.get_text(strip=True)

    review_summary = ReviewSummary(
        GoodFor=good_for,
        NotSoGoodFor=not_so_good_for,
        Conclusion=conclusion,
    )

    return executive_summary, review_summary, review_score


def extract_review_data(
    overview_soup: BeautifulSoup, review_soup: Optional[BeautifulSoup] = None
) -> tuple[ReviewData, int]:
    """Extract review data from overview and review pages.

    Priority for ExecutiveSummary:
    1. Overview page product description (primary source)
    2. Review page intro (fallback)

    Returns:
        Tuple of (review_data, review_score)
    """
    review_data = ReviewData()
    review_score = 0

    # Product photos from thumbnail gallery
    thumbnails = overview_soup.select("div.productShotThumbnail")
    if thumbnails:
        photos = []
        for thumb in thumbnails:
            style = thumb.get("style", "")
            clean_url = extract_clean_url_from_style(style)
            if clean_url:
                photos.append(clean_url)
        review_data.ProductPhotos = photos

    # ASIN (Amazon product IDs)
    asins = []
    amazon_links = overview_soup.select("a.amazonAffiliate[data-product-id]")
    for link in amazon_links:
        asin = link.get("data-product-id")
        if asin:
            asins.append(asin)

    if not asins:
        amazon_links = overview_soup.select("a[href*='amazon.com']")
        for link in amazon_links:
            href = link.get("href", "")
            match = re.search(r"/dp/([A-Z0-9]{10})", href)
            if match:
                asins.append(match.group(1))

    review_data.ASIN = list(set(asins))

    # Priority 1: ExecutiveSummary from overview page
    overview_summary = _extract_overview_summary(overview_soup)
    if overview_summary:
        review_data.ExecutiveSummary = overview_summary
        logger.debug("Using overview page product description for executive summary")

    # Parse review page if available
    if review_soup:
        executive_summary_from_review, review_summary, review_score = _parse_review_page(review_soup)
        review_data.ReviewSummary = review_summary

        # Priority 2: Fallback to review page intro
        if not review_data.ExecutiveSummary and executive_summary_from_review:
            review_data.ExecutiveSummary = executive_summary_from_review
            logger.debug("Using review page intro as fallback for executive summary")
    else:
        review_data.ReviewSummary = ReviewSummary(
            GoodFor="",
            NotSoGoodFor="",
            Conclusion="",
        )

    # Try JSON-LD for review score
    if review_score == 0:
        json_ld = overview_soup.select_one('script[type="application/ld+json"]')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict) and "review" in data:
                    review = data["review"]
                    if isinstance(review, dict) and "reviewRating" in review:
                        rating = review["reviewRating"]
                        if isinstance(rating, dict) and "ratingValue" in rating:
                            review_score = int(rating["ratingValue"])
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD: {e}")

    return review_data, review_score
