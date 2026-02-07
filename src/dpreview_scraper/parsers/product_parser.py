"""Parse DPReview product pages."""

import re
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from dpreview_scraper.models.camera import Camera
from dpreview_scraper.models.review import ReviewData, ReviewSummary
from dpreview_scraper.models.specs import CameraSpecs
from dpreview_scraper.utils.logging import logger

# Constants for parsing
OVERVIEW_SUFFIX = " Overview"

# Precompiled regex patterns
URL_FROM_CSS_PATTERN = re.compile(r'url\(["\']?([^"\'()]+)["\']?\)')
DPREVIEW_SIZE_PARAM_PATTERN = re.compile(r'TS\d+x\d+~')
BULLET_POINT_PATTERN = re.compile(r'\s*[•·].*', re.DOTALL)
ANNOUNCED_PREFIX_PATTERN = re.compile(r'^Announced\s+')
MULTIPLE_SPACES_PATTERN = re.compile(r'\s+')
# Pattern to remove spaces before inch/quote symbols
SPACE_BEFORE_INCH_PATTERN = re.compile(r'\s+(″|"|\'\'|")')
# Pattern to remove spaces before closing parentheses
SPACE_BEFORE_PAREN_PATTERN = re.compile(r'\s+\)')

# Fields that should be parsed as lists
LIST_SPEC_FIELDS = frozenset({
    "Autofocus", "ExposureModes", "MeteringModes",
    "FileFormat", "Modes", "DriveModes"
})


def parse_product_page(
    overview_html: str,
    specs_html: str,
    review_html: Optional[str],
    review_specs_html: Optional[str],
    product_code: str,
    url: str,
    short_specs: Optional[List[str]] = None,
) -> Camera:
    """Parse complete product page.

    Args:
        overview_html: Product overview page HTML
        specs_html: Product specifications page HTML
        review_html: Product review page HTML (optional)
        review_specs_html: Review specs page HTML (page 2 of review, more comprehensive)
        product_code: Product code
        url: Product URL
        short_specs: Short specs from search results (optional, preferred over extracting from overview)

    Returns:
        Camera object with all data
    """
    overview_soup = BeautifulSoup(overview_html, "lxml")
    specs_soup = BeautifulSoup(specs_html, "lxml")
    review_soup = BeautifulSoup(review_html, "lxml") if review_html else None
    review_specs_soup = BeautifulSoup(review_specs_html, "lxml") if review_specs_html else None

    # Extract top-level metadata from overview page
    name = _extract_name(overview_soup)
    image_url = _extract_image_url(overview_soup)
    # Use short_specs from search results if provided, otherwise extract from overview (fallback)
    if short_specs is None:
        short_specs = _extract_short_specs(overview_soup)
    award = _extract_award(overview_soup)

    # Extract specs: prioritize review specs (more comprehensive), fallback to regular specs
    if review_specs_soup:
        logger.debug("Using review specs page (more comprehensive)")
        specs = _extract_review_specs(review_specs_soup)
        # Merge with regular specs to fill any gaps
        regular_specs = _extract_full_specs(specs_soup)
        specs = _merge_specs(specs, regular_specs)
    else:
        # No review, use regular specs page
        specs = _extract_full_specs(specs_soup)

    # Extract announced date from overview page (not in specs table)
    announced = _extract_announced(overview_soup)
    if announced and not specs.Announced:
        specs.Announced = announced

    # Extract review data from overview and review pages
    review_data, review_score = _extract_review_data(overview_soup, review_soup)

    # Extract or construct ReviewPreview if not already in specs
    if not specs.ReviewPreview and review_score > 0:
        review_preview = _extract_review_preview(overview_soup, review_score, award)
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


def _extract_clean_url_from_style(style: str) -> str:
    """Extract URL from CSS background-image style and remove size parameters.

    Args:
        style: CSS style string containing background-image: url(...)

    Returns:
        Clean URL with size parameters removed, or empty string if no match
    """
    match = URL_FROM_CSS_PATTERN.search(style)
    if match:
        url = match.group(1)
        return DPREVIEW_SIZE_PARAM_PATTERN.sub('', url)
    return ""


def _extract_name(soup: BeautifulSoup) -> str:
    """Extract camera name."""
    # Extract from h1, which contains "[Name] Overview"
    h1 = soup.select_one("h1")
    if h1:
        title = h1.get_text(strip=True)
        # Remove " Overview" suffix if present
        if title.endswith(OVERVIEW_SUFFIX):
            return title[:-len(OVERVIEW_SUFFIX)]
        return title

    # Fallback: try breadcrumbs
    breadcrumb = soup.select_one("div.breadcrumbs a.item:last-child")
    if breadcrumb:
        return breadcrumb.get_text(strip=True)

    return ""


def _extract_image_url(soup: BeautifulSoup) -> str:
    """Extract main product image URL (not product photos from gallery)."""
    # Priority order for main product image selectors
    main_image_selectors = [
        "div#productImage",           # Primary selector for main product image
        "div.productImage",           # Alternative class-based selector
        "div.mainProductImage",       # Another common pattern
        "div.productImageMain",       # Yet another pattern
    ]

    for selector in main_image_selectors:
        element = soup.select_one(selector)
        if element:
            # Try to extract from background-image style
            style = element.get("style", "")
            if style:
                clean_url = _extract_clean_url_from_style(style)
                if clean_url:
                    # Ensure it's NOT a product shot (shots/ path indicates gallery photos)
                    if "/shots/" not in clean_url:
                        logger.debug(f"Found main product image with selector '{selector}': {clean_url}")
                        return clean_url
                    else:
                        logger.debug(f"Skipping gallery photo from selector '{selector}': {clean_url}")

            # Try to extract from img tag if no background-image
            img = element.find("img")
            if img:
                src = img.get("src", "")
                if src and "/shots/" not in src:
                    clean_url = DPREVIEW_SIZE_PARAM_PATTERN.sub('', src)
                    logger.debug(f"Found main product image from img tag with selector '{selector}': {clean_url}")
                    return clean_url

    # Last resort: use first thumbnail ONLY if no main image found
    # This is not ideal but better than returning empty
    thumbnail = soup.select_one("div.productShotThumbnail")
    if thumbnail:
        style = thumbnail.get("style", "")
        clean_url = _extract_clean_url_from_style(style)
        if clean_url:
            logger.warning(f"Using fallback thumbnail for main image (main image not found): {clean_url}")
            return clean_url

    logger.warning("No product image found")
    return ""


def _extract_short_specs(soup: BeautifulSoup) -> List[str]:
    """Extract short specs (key features)."""
    specs = []

    # Short specs are in the quick specs table on the right
    quick_specs_table = soup.select_one("div.rightColumn.quickSpecs table")
    if quick_specs_table:
        rows = quick_specs_table.select("tr")
        for row in rows:
            label_elem = row.select_one("th.label")
            value_elem = row.select_one("td.value")
            if label_elem and value_elem:
                label = label_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                # Combine into a readable spec
                specs.append(f"{value}")

    return specs


def _extract_award(soup: BeautifulSoup) -> str:
    """Extract review award (gold, silver, bronze, recommended) for the current product.

    Important: Only extracts award from the current product's badge/score section,
    not from related products in sidebars or other page elements.
    """
    # Priority 1: Look for productBadgeAndScore div with award class
    # This is the main product review badge (e.g., <div class="productBadgeAndScore gold ...">)
    badge_elem = soup.select_one("div.productBadgeAndScore")
    if badge_elem:
        classes = badge_elem.get("class", [])
        for cls in classes:
            if cls in ["gold", "silver", "bronze"]:
                logger.debug(f"Found award '{cls}' in productBadgeAndScore")
                return cls
        # Also check for "recommended" in the text
        text = badge_elem.get_text(strip=True).lower()
        if "recommended" in text:
            logger.debug("Found 'recommended' in productBadgeAndScore text")
            return "recommended"

    # Priority 2: Look for award within review preview sections (scoped to current product)
    # These sections are specific to the current product, not other products
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
            # Look for award span within this section
            award_elem = section.select_one("span.award")
            if award_elem:
                classes = award_elem.get("class", [])
                for cls in classes:
                    if cls in ["gold", "silver", "bronze"]:
                        logger.debug(f"Found award '{cls}' in review section: {section_selector}")
                        return cls

            # Check for award in text within this section
            text = section.get_text(strip=True).lower()
            if "gold award" in text:
                logger.debug(f"Found 'gold award' text in review section: {section_selector}")
                return "gold"
            elif "silver award" in text:
                logger.debug(f"Found 'silver award' text in review section: {section_selector}")
                return "silver"
            elif "bronze award" in text:
                logger.debug(f"Found 'bronze award' text in review section: {section_selector}")
                return "bronze"
            elif "recommended" in text:
                logger.debug(f"Found 'recommended' text in review section: {section_selector}")
                return "recommended"

    # Priority 3: Check for badge/data-award attributes (but still scope to main content, not sidebar)
    # Avoid sidebars by looking only in main content areas
    main_content_selectors = [
        "div.mainContent [data-award]",
        "div.leftColumn [data-award]",
        "div.mainContent .badge",
        "div.leftColumn .badge",
    ]

    for selector in main_content_selectors:
        elem = soup.select_one(selector)
        if elem:
            # Try data-award attribute first
            data_award = elem.get("data-award", "").lower()
            if data_award in ["gold", "silver", "bronze", "recommended"]:
                logger.debug(f"Found award '{data_award}' from data-award attribute")
                return data_award

            # Try text content
            text = elem.get_text(strip=True).lower()
            if "gold" in text:
                logger.debug(f"Found 'gold' in badge text")
                return "gold"
            elif "silver" in text:
                logger.debug(f"Found 'silver' in badge text")
                return "silver"
            elif "bronze" in text:
                logger.debug(f"Found 'bronze' in badge text")
                return "bronze"
            elif "recommended" in text:
                logger.debug(f"Found 'recommended' in badge text")
                return "recommended"

    logger.debug("No award found for this product")
    return ""


def _extract_review_preview(soup: BeautifulSoup, review_score: int, award: str) -> str:
    """Extract review preview text from overview page.

    The review preview typically appears in a sidebar or section showing:
    - Review score percentage (e.g., "92%")
    - Award (e.g., "Gold Award")
    - "Read review ..." text
    - Review date (e.g., "Jan 31, 2023")

    Args:
        soup: BeautifulSoup object of overview page
        review_score: Review score (0-100)
        award: Award level (gold, silver, bronze, etc.)

    Returns:
        Formatted review preview text, or empty string if not available
    """
    # Try to find review preview section in HTML
    # Common selectors for review preview boxes
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
            # Get text content preserving whitespace/newlines
            text = elem.get_text(separator='\n', strip=False)
            # Check if it contains review-related content
            if review_score > 0 and (
                str(review_score) in text or
                'review' in text.lower() or
                award.lower() in text.lower()
            ):
                logger.debug(f"Found review preview with selector: {selector}")
                return text.strip()

    # Fallback: construct from available data if review exists
    if review_score > 0:
        # Format award text
        award_text = f"{award.title()} Award" if award else ""

        # Try to find review date from overview page
        review_date = ""
        # Look for review date in various locations
        date_elem = soup.select_one("div.reviewDate, span.reviewDate, div.review span.date")
        if date_elem:
            review_date = date_elem.get_text(strip=True)

        # Construct preview in expected format
        preview_parts = [
            f"{review_score}%{award_text}",
            "Read review ...",
        ]
        if review_date:
            preview_parts.append(review_date)

        return "\n".join(preview_parts)

    return ""


def _extract_announced(soup: BeautifulSoup) -> str:
    """Extract announced date from overview page.

    The announced date appears in a section like:
    <span class="greyLabel">Announced</span>
    Oct 26, 2022
    """
    # Find the "Announced" label span
    announced_label = soup.find("span", class_="greyLabel", string="Announced")
    if announced_label:
        # The date is the immediate next sibling text after the span
        next_sibling = announced_label.next_sibling
        if next_sibling:
            # Get the text and clean it up
            date_text = str(next_sibling).strip()
            # Remove bullet point and anything after (format: "Oct 26, 2022\n •")
            date_text = BULLET_POINT_PATTERN.sub('', date_text)
            date_text = date_text.strip()
            if date_text:
                return date_text
    return ""


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text by collapsing multiple spaces to single space.

    Also removes spaces before inch symbols (″) and closing parentheses.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    # First collapse multiple spaces
    text = MULTIPLE_SPACES_PATTERN.sub(' ', text)
    # Remove spaces before inch/quote symbols
    text = SPACE_BEFORE_INCH_PATTERN.sub(r'\1', text)
    # Remove spaces before closing parentheses
    text = SPACE_BEFORE_PAREN_PATTERN.sub(')', text)
    return text.strip()


def _parse_spec_row(
    row: Tag,
    label_selector: str,
    value_selector: str
) -> Optional[tuple[str, str | list]]:
    """Parse a single spec row, returning (field_name, value) or None.

    Args:
        row: BeautifulSoup Tag for the table row
        label_selector: CSS selector for the label element
        value_selector: CSS selector for the value element

    Returns:
        Tuple of (field_name, value) or None if row can't be parsed
    """
    label_elem = row.select_one(label_selector)
    value_elem = row.select_one(value_selector)

    if not label_elem or not value_elem:
        return None

    label = label_elem.get_text(strip=True).replace(":", "")
    value = _normalize_whitespace(value_elem.get_text(separator=' ', strip=True))

    if not value:
        return None

    field_name = _normalize_spec_name(label)
    if not field_name:
        logger.debug(f"UNMAPPED LABEL: '{label}' = '{value[:50] if len(value) > 50 else value}'")
        return None

    # Parse as list if needed
    if field_name in LIST_SPEC_FIELDS:
        return (field_name, _parse_list_value(value_elem))

    # Post-process specific fields
    if field_name == "Announced":
        value = ANNOUNCED_PREFIX_PATTERN.sub('', value)

    return (field_name, value)


def _extract_review_specs(soup: BeautifulSoup) -> CameraSpecs:
    """Extract specs from review page 2 (table.contentTable).

    Review specs pages have more comprehensive data than the regular specs page.
    """
    specs_dict: dict[str, str | list] = {}

    # Review specs are in table.contentTable
    content_tables = soup.select("table.contentTable")
    if not content_tables:
        logger.warning("No contentTable found on review specs page")
        return CameraSpecs(**specs_dict)

    for table in content_tables:
        rows = table.select("tr")

        for row in rows:
            try:
                result = _parse_spec_row(row, "th", "td")
                if result:
                    field_name, value = result
                    specs_dict[field_name] = value
            except Exception as e:
                logger.debug(f"Failed to parse review spec row: {e}")
                continue

    return CameraSpecs(**specs_dict)


def _merge_specs(primary: CameraSpecs, secondary: CameraSpecs) -> CameraSpecs:
    """Merge two CameraSpecs, using primary values and filling gaps from secondary.

    Args:
        primary: Primary specs (higher priority, e.g., from review)
        secondary: Secondary specs (lower priority, e.g., from regular specs page)

    Returns:
        Merged CameraSpecs object
    """
    # Get all fields from CameraSpecs (Pydantic model)
    merged_dict = {}

    for field_name in primary.model_fields:
        primary_value = getattr(primary, field_name)
        secondary_value = getattr(secondary, field_name)

        # Use primary if it has a value, otherwise use secondary
        if primary_value:
            # For lists, check if non-empty
            if isinstance(primary_value, list):
                merged_dict[field_name] = primary_value if primary_value else secondary_value
            else:
                merged_dict[field_name] = primary_value
        else:
            merged_dict[field_name] = secondary_value

    return CameraSpecs(**merged_dict)


def _extract_full_specs(soup: BeautifulSoup) -> CameraSpecs:
    """Extract all technical specifications from full specifications page."""
    specs_dict: dict[str, str | list] = {}

    # Specs are in the full specifications table
    specs_table = soup.select_one("table.specsTable.compact")
    if not specs_table:
        logger.warning("No specifications table found")
        return CameraSpecs(**specs_dict)

    # Parse all tbody sections (each group of specs)
    tbody_sections = specs_table.select("tbody")

    for tbody in tbody_sections:
        rows = tbody.select("tr")

        for row in rows:
            try:
                result = _parse_spec_row(row, "th.label", "td.value")
                if result:
                    field_name, value = result
                    specs_dict[field_name] = value
            except Exception as e:
                logger.debug(f"Failed to parse spec row: {e}")
                continue

    return CameraSpecs(**specs_dict)


def _normalize_spec_name(label: str) -> Optional[str]:
    """Normalize spec label to field name."""
    # Mapping of common label variations to field names
    mapping = {
        # Dates & Pricing
        "announced": "Announced",
        "announcement date": "Announced",
        "msrp": "MSRP",
        "price": "BuyingOptions",
        "buying options": "BuyingOptions",

        # Body & Build
        "body type": "BodyType",
        "body material": "BodyMaterial",
        "dimensions": "Dimensions",
        "weight (inc. batteries)": "WeightIncBatteries",
        "weight": "WeightIncBatteries",
        "durability": "Durability",
        "environmentally sealed": "EnvironmentallySealed",

        # Sensor
        "sensor type": "SensorType",
        "sensor": "SensorType",
        "sensor size": "SensorSize",
        "effective pixels": "EffectivePixels",
        "megapixels": "EffectivePixels",
        "processor": "Processor",
        "image processor": "Processor",
        "focal length multiplier": "FocalLengthMultiplier",
        "crop factor": "FocalLengthMultiplier",
        "sensor photo detectors": "SensorPhotoDetectors",

        # ISO
        "iso": "ISO",
        "iso sensitivity": "ISO",
        "boosted iso maximum": "BoostedISOMaximum",
        "boosted iso minimum": "BoostedISOMinimum",
        "boosted iso (maximum)": "BoostedISOMaximum",
        "boosted iso (minimum)": "BoostedISOMinimum",
        "iso (boosted)": "BoostedISOMaximum",
        "extended iso": "BoostedISOMaximum",

        # Autofocus
        "autofocus": "Autofocus",
        "af system": "Autofocus",
        "autofocus assist lamp": "AutofocusAssistLamp",
        "af assist lamp": "AutofocusAssistLamp",
        "af assist": "AutofocusAssistLamp",
        "number of focus points": "NumberOfFocusPoints",
        "focus points": "NumberOfFocusPoints",

        # Exposure & Metering
        "ae bracketing": "AEBracketing",
        "auto exposure bracketing": "AEBracketing",
        "aperture priority": "AperturePriority",
        "exposure compensation": "ExposureCompensation",
        "exposure modes": "ExposureModes",
        "manual exposure mode": "ManualExposureMode",
        "metering modes": "MeteringModes",
        "shutter priority": "ShutterPriority",

        # Shutter
        "maximum shutter speed": "MaximumShutterSpeed",
        "max shutter speed": "MaximumShutterSpeed",
        "maximum shutter speed (electronic)": "MaximumShutterSpeedElectronic",
        "minimum shutter speed": "MinimumShutterSpeed",
        "min shutter speed": "MinimumShutterSpeed",

        # Screen
        "screen size": "ScreenSize",
        "screen": "ScreenSize",
        "lcd": "ScreenSize",
        "screen dots": "ScreenDots",
        "screen resolution": "ScreenDots",
        "screen type": "ScreenType",
        "touch screen": "TouchScreen",
        "articulated lcd": "ArticulatedLCD",
        "articulating screen": "ArticulatedLCD",

        # Viewfinder
        "viewfinder type": "ViewfinderType",
        "viewfinder": "ViewfinderType",
        "viewfinder coverage": "ViewfinderCoverage",
        "viewfinder magnification": "ViewfinderMagnification",
        "viewfinder resolution": "ViewfinderResolution",
        "field of view": "FieldOfView",

        # Video
        "format": "Format",
        "video format": "Format",
        "modes": "Modes",
        "video modes": "Modes",
        "resolutions": "Resolutions",
        "video resolutions": "Resolutions",
        "microphone": "Microphone",
        "microphone port": "MicrophonePort",
        "speaker": "Speaker",
        "headphone port": "HeadphonePort",
        "timelapse recording": "TimelapseRecording",

        # Image
        "color filter array": "ColorFilterArray",
        "color filter": "ColorFilterArray",
        "color space": "ColorSpace",
        "color spaces": "ColorSpace",
        "custom white balance": "CustomWhiteBalance",
        "file format": "FileFormat",
        "image ratio w:h": "ImageRatioWh",
        "image ratio wh": "ImageRatioWh",
        "aspect ratio": "ImageRatioWh",
        "jpeg quality levels": "JPEGQualityLevels",
        "max resolution": "MaxResolution",
        "maximum resolution": "MaxResolution",
        "other resolutions": "OtherResolutions",
        "uncompressed format": "UncompressedFormat",
        "raw format": "UncompressedFormat",
        "wb bracketing": "WBBracketing",
        "white balance presets": "WhiteBalancePresets",

        # Flash
        "built-in flash": "BuiltInFlash",
        "built in flash": "BuiltInFlash",
        "external flash": "ExternalFlash",
        "flash modes": "FlashModes",
        "flash range": "FlashRange",
        "flash x-sync speed": "FlashXSyncSpeed",
        "flash x sync speed": "FlashXSyncSpeed",
        "flash sync speed": "FlashXSyncSpeed",

        # Battery
        "battery": "Battery",
        "battery description": "BatteryDescription",
        "battery life (cipa)": "BatteryLifeCIPA",
        "battery life": "BatteryLifeCIPA",

        # Connectivity
        "usb": "USB",
        "wireless": "Wireless",
        "wifi": "Wireless",
        "wi-fi": "Wireless",
        "bluetooth": "WirelessNotes",
        "wireless notes": "WirelessNotes",
        "gps": "GPS",
        "gps notes": "GPSNotes",
        "hdmi": "HDMI",
        "remote control": "RemoteControl",
        "usb charging": "USBCharging",

        # Lens & Optics
        "lens mount": "LensMount",
        "mount": "LensMount",

        # Storage
        "storage": "StorageTypes",
        "storage types": "StorageTypes",
        "memory card": "StorageTypes",

        # Other Features
        "image stabilization": "ImageStabilization",
        "cipa image stabilization rating": "CIPAImageStabilizationRating",
        "image stabilization notes": "ImageStabilizationNotes",
        "continuous drive": "ContinuousDrive",
        "drive modes": "DriveModes",
        "live view": "LiveView",
        "manual focus": "ManualFocus",
        "orientation sensor": "OrientationSensor",
        "self-timer": "SelfTimer",
        "digital zoom": "DigitalZoom",
        "scene modes": "SceneModes",
        "subject / scene modes": "SubjectSceneModes",
        "review preview": "ReviewPreview",
    }

    label_lower = label.lower().strip()
    return mapping.get(label_lower)


def _parse_list_value(elem: Tag) -> List[str]:
    """Parse value that should be a list."""
    items = []

    # Check for <ul> or <ol>
    ul = elem.find("ul") or elem.find("ol")
    if ul:
        for li in ul.find_all("li"):
            # Use separator=' ' to preserve spaces between text nodes
            text = _normalize_whitespace(li.get_text(separator=' ', strip=True))
            if text:
                items.append(text)
    else:
        # Parse comma-separated or line-break separated
        # Use separator=' ' to preserve spaces
        text = _normalize_whitespace(elem.get_text(separator=' ', strip=True))
        # Try splitting by common separators
        for sep in ["\n", ";", ","]:
            if sep in text:
                parts = [_normalize_whitespace(p) for p in text.split(sep) if p.strip()]
                if len(parts) > 1:
                    return parts

        # Single item
        if text.strip():
            items.append(text.strip())

    return items


def _extract_overview_summary(soup: BeautifulSoup) -> str:
    """Extract summary/description from the overview page's description tab.

    This is the primary source for ExecutiveSummary - the manufacturer's
    product description from the main product page.
    """
    # Priority order: Description tab content, then other product description sections
    selectors = [
        # Product overview page - manufacturer description paragraph (most common)
        "div.productOverviewPage div.section p",
        # Description tab content
        "div#descriptionTab div.productBody",
        "div#description div.productBody",
        "div.descriptionTab div.productBody",
        # Product description section on overview page
        "div.productDescription div.productBody",
        "div.productDescription",
        "div.product-description",
        # Main product body text
        "div.productBody",
        "div#productBody",
        # Main content paragraph
        "div.leftColumn div.description p",
        "div.mainContent p.intro",
        # Press release or announcement text
        "div.pressRelease",
        "div.announcement",
    ]

    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(separator=' ', strip=True)
            logger.debug(f"Selector '{selector}' matched element with {len(text)} chars")
            if text and len(text) > 100:
                # Filter out blog/promo content using word boundary matching
                blog_patterns = [
                    r'\bthis month\b',
                    r'\bchallenge\b',
                    r'\bshare your\b',
                    r'\bphoto adventures\b',
                ]
                text_lower = text.lower()
                if any(re.search(pattern, text_lower) for pattern in blog_patterns):
                    logger.debug(f"Skipping blog-like content from selector: {selector}")
                    continue

                logger.debug(f"Found executive summary from overview page with selector: {selector}")
                logger.debug(f"Text preview: {text[:100]}...")
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

    # Try to extract executive summary from the main review content area
    # Must be specific to avoid matching sidebar/promotional content
    # DPReview review pages have the intro within the main article content
    summary_selectors = [
        # Main review article intro - scoped to main content area
        "div.mainContent div.article-intro",
        "div.content div.article-intro",
        "article div.article-intro",
        # Review intro section - more specific
        "div.reviewIntro",
        "div.review-intro",
        # Fallback: first paragraph in the main article body
        "div.mainContent div.articleBody p:first-of-type",
        "div.content div.articleBody p:first-of-type",
        "article div.articleBody p:first-of-type",
        # Overview page description
        "div.productDescription",
        "div.product-description",
    ]

    for selector in summary_selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(strip=True)
            # Ensure it's substantial and looks like camera content (not blog/promo)
            if text and len(text) > 50:
                # Skip if it looks like unrelated blog content - use word boundaries
                blog_patterns = [
                    r'\bthis month\b',
                    r'\bchallenge\b',
                    r'\bshare your\b',
                    r'\bphoto adventures\b',
                ]
                text_lower = text.lower()
                if any(re.search(pattern, text_lower) for pattern in blog_patterns):
                    logger.debug(f"Skipping blog-like content from selector: {selector}")
                    continue
                executive_summary = text
                logger.debug(f"Found executive summary with selector: {selector}")
                break

    # Try to extract review score
    score_selectors = [
        "span.overallScore",
        "span.score",
        "div.score",
        "[data-score]",
    ]

    for selector in score_selectors:
        elem = soup.select_one(selector)
        if elem:
            # Try to get score from text or data attribute
            score_text = elem.get_text(strip=True)
            data_score = elem.get("data-score")

            score_value = data_score or score_text
            if score_value:
                try:
                    # Extract numeric value (handle formats like "85" or "85%")
                    score_match = re.search(r"(\d+)", score_value)
                    if score_match:
                        review_score = int(score_match.group(1))
                        logger.debug(f"Found review score: {review_score} with selector: {selector}")
                        break
                except (ValueError, AttributeError):
                    continue

    # Extract Good For / Not So Good For using DPReview-specific selectors
    # DPReview uses: <tr class="suitability goodFor"><td>...<div class="text">content</div>
    good_for_elem = soup.select_one("tr.suitability.goodFor div.text")
    if good_for_elem:
        good_for = good_for_elem.get_text(strip=True)
        logger.debug(f"Found 'Good For': {good_for[:50]}...")

    not_good_elem = soup.select_one("tr.suitability.notGoodFor div.text")
    if not_good_elem:
        not_so_good_for = not_good_elem.get_text(strip=True)
        logger.debug(f"Found 'Not So Good For': {not_so_good_for[:50]}...")

    # Extract conclusion from summary section
    # DPReview uses: <tr class="summary"><td><div class="summary">text</div>
    conclusion_elem = soup.select_one("tr.summary div.summary")
    if conclusion_elem:
        conclusion = conclusion_elem.get_text(strip=True)
        logger.debug(f"Found conclusion: {conclusion[:50]}...")

    review_summary = ReviewSummary(
        GoodFor=good_for,
        NotSoGoodFor=not_so_good_for,
        Conclusion=conclusion,
    )

    return executive_summary, review_summary, review_score


def _extract_review_data(
    overview_soup: BeautifulSoup, review_soup: Optional[BeautifulSoup] = None
) -> tuple[ReviewData, int]:
    """Extract review data.

    Priority for ExecutiveSummary:
    1. Overview page product description (primary source)
    2. Review page intro (fallback)

    Returns:
        Tuple of (review_data, review_score)
    """
    review_data = ReviewData()
    review_score = 0

    # Product photos - extract from thumbnail gallery on overview page
    thumbnails = overview_soup.select("div.productShotThumbnail")
    if thumbnails:
        photos = []
        for thumb in thumbnails:
            style = thumb.get("style", "")
            clean_url = _extract_clean_url_from_style(style)
            if clean_url:
                photos.append(clean_url)
        review_data.ProductPhotos = photos

    # ASIN (Amazon product IDs) - from overview page
    asins = []
    # Look for data-product-id attribute on Amazon affiliate links
    amazon_links = overview_soup.select("a.amazonAffiliate[data-product-id]")
    for link in amazon_links:
        asin = link.get("data-product-id")
        if asin:
            asins.append(asin)

    # Also check href for /dp/ pattern
    if not asins:
        amazon_links = overview_soup.select("a[href*='amazon.com']")
        for link in amazon_links:
            href = link.get("href", "")
            match = re.search(r"/dp/([A-Z0-9]{10})", href)
            if match:
                asins.append(match.group(1))

    review_data.ASIN = list(set(asins))  # Remove duplicates

    # PRIORITY 1: Extract ExecutiveSummary from overview page's product description tab
    # This is the primary source - manufacturer's description
    overview_summary = _extract_overview_summary(overview_soup)
    if overview_summary:
        review_data.ExecutiveSummary = overview_summary
        logger.debug("Using overview page product description for executive summary")

    # Parse review page content if available
    if review_soup:
        executive_summary_from_review, review_summary, review_score = _parse_review_page(review_soup)
        review_data.ReviewSummary = review_summary

        # PRIORITY 2: Only use review page intro if overview page had no description
        if not review_data.ExecutiveSummary and executive_summary_from_review:
            review_data.ExecutiveSummary = executive_summary_from_review
            logger.debug("Using review page intro as fallback for executive summary")
    else:
        # No review page available - use empty values
        review_data.ReviewSummary = ReviewSummary(
            GoodFor="",
            NotSoGoodFor="",
            Conclusion="",
        )

    # Try to extract review score from JSON-LD on overview page if not found in review
    if review_score == 0:
        json_ld = overview_soup.select_one('script[type="application/ld+json"]')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                # Look for review rating
                if isinstance(data, dict) and "review" in data:
                    review = data["review"]
                    if isinstance(review, dict) and "reviewRating" in review:
                        rating = review["reviewRating"]
                        if isinstance(rating, dict) and "ratingValue" in rating:
                            review_score = int(rating["ratingValue"])
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD: {e}")

    return review_data, review_score
