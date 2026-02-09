"""Extract top-level camera metadata from overview pages."""

import re
from typing import List

from bs4 import BeautifulSoup

from dpreview_scraper.parsers.parse_utils import (
    DPREVIEW_SIZE_PARAM_PATTERN,
    extract_clean_url_from_style,
)
from dpreview_scraper.utils.logging import logger

OVERVIEW_SUFFIX = " Overview"
BULLET_POINT_PATTERN = re.compile(r'\s*[•·].*', re.DOTALL)


def extract_name(soup: BeautifulSoup) -> str:
    """Extract camera name from overview page."""
    h1 = soup.select_one("h1")
    if h1:
        title = h1.get_text(strip=True)
        if title.endswith(OVERVIEW_SUFFIX):
            return title[:-len(OVERVIEW_SUFFIX)]
        return title

    breadcrumb = soup.select_one("div.breadcrumbs a.item:last-child")
    if breadcrumb:
        return breadcrumb.get_text(strip=True)

    return ""


def extract_image_url(soup: BeautifulSoup) -> str:
    """Extract main product image URL (not product photos from gallery)."""
    main_image_selectors = [
        "div#productImage",
        "div.productImage",
        "div.mainProductImage",
        "div.productImageMain",
    ]

    for selector in main_image_selectors:
        element = soup.select_one(selector)
        if element:
            style = element.get("style", "")
            if style:
                clean_url = extract_clean_url_from_style(style)
                if clean_url:
                    if "/shots/" not in clean_url:
                        logger.debug(f"Found main product image with selector '{selector}': {clean_url}")
                        return clean_url
                    else:
                        logger.debug(f"Skipping gallery photo from selector '{selector}': {clean_url}")

            img = element.find("img")
            if img:
                src = img.get("src", "")
                if src and "/shots/" not in src:
                    clean_url = DPREVIEW_SIZE_PARAM_PATTERN.sub('', src)
                    logger.debug(f"Found main product image from img tag with selector '{selector}': {clean_url}")
                    return clean_url

    thumbnail = soup.select_one("div.productShotThumbnail")
    if thumbnail:
        style = thumbnail.get("style", "")
        clean_url = extract_clean_url_from_style(style)
        if clean_url:
            logger.warning(f"Using fallback thumbnail for main image (main image not found): {clean_url}")
            return clean_url

    logger.warning("No product image found")
    return ""


def extract_short_specs(soup: BeautifulSoup) -> List[str]:
    """Extract short specs (key features) from overview page."""
    specs = []

    quick_specs_table = soup.select_one("div.rightColumn.quickSpecs table")
    if quick_specs_table:
        rows = quick_specs_table.select("tr")
        for row in rows:
            label_elem = row.select_one("th.label")
            value_elem = row.select_one("td.value")
            if label_elem and value_elem:
                value = value_elem.get_text(strip=True)
                specs.append(f"{value}")

    return specs


def extract_award(soup: BeautifulSoup) -> str:
    """Extract review award (gold, silver, bronze, recommended) for the current product."""
    badge_elem = soup.select_one("div.productBadgeAndScore")
    if badge_elem:
        classes = badge_elem.get("class", [])
        for cls in classes:
            if cls in ["gold", "silver", "bronze"]:
                logger.debug(f"Found award '{cls}' in productBadgeAndScore")
                return cls
        text = badge_elem.get_text(strip=True).lower()
        if "recommended" in text:
            logger.debug("Found 'recommended' in productBadgeAndScore text")
            return "recommended"

    review_sections = [
        "div.reviewPreview",
        "div.review-preview",
        "td.review",
        "div.productReview",
        "div.reviewInfo",
    ]

    for section_selector in review_sections:
        section = soup.select_one(section_selector)
        if section:
            award_elem = section.select_one("span.award")
            if award_elem:
                classes = award_elem.get("class", [])
                for cls in classes:
                    if cls in ["gold", "silver", "bronze"]:
                        logger.debug(f"Found award '{cls}' in review section: {section_selector}")
                        return cls

            text = section.get_text(strip=True).lower()
            if "gold award" in text:
                return "gold"
            elif "silver award" in text:
                return "silver"
            elif "bronze award" in text:
                return "bronze"
            elif "recommended" in text:
                return "recommended"

    main_content_selectors = [
        "div.mainContent [data-award]",
        "div.leftColumn [data-award]",
        "div.mainContent .badge",
        "div.leftColumn .badge",
    ]

    for selector in main_content_selectors:
        elem = soup.select_one(selector)
        if elem:
            data_award = elem.get("data-award", "").lower()
            if data_award in ["gold", "silver", "bronze", "recommended"]:
                return data_award

            text = elem.get_text(strip=True).lower()
            for award in ["gold", "silver", "bronze", "recommended"]:
                if award in text:
                    return award

    logger.debug("No award found for this product")
    return ""


def extract_review_preview(soup: BeautifulSoup, review_score: int, award: str) -> str:
    """Extract review preview text from overview page."""
    preview_selectors = [
        "div.reviewPreview",
        "div.review-preview",
        "td.review",
        "div.productReview",
        "div.reviewInfo",
    ]

    for selector in preview_selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(separator='\n', strip=False)
            if review_score > 0 and (
                str(review_score) in text or
                'review' in text.lower() or
                award.lower() in text.lower()
            ):
                logger.debug(f"Found review preview with selector: {selector}")
                return text.strip()

    if review_score > 0:
        award_text = f"{award.title()} Award" if award else ""
        review_date = ""
        date_elem = soup.select_one("div.reviewDate, span.reviewDate, div.review span.date")
        if date_elem:
            review_date = date_elem.get_text(strip=True)

        preview_parts = [
            f"{review_score}%{award_text}",
            "Read review ...",
        ]
        if review_date:
            preview_parts.append(review_date)

        return "\n".join(preview_parts)

    return ""


def extract_announced(soup: BeautifulSoup) -> str:
    """Extract announced date from overview page."""
    announced_label = soup.find("span", class_="greyLabel", string="Announced")
    if announced_label:
        next_sibling = announced_label.next_sibling
        if next_sibling:
            date_text = str(next_sibling).strip()
            date_text = BULLET_POINT_PATTERN.sub('', date_text)
            date_text = date_text.strip()
            if date_text:
                return date_text
    return ""
