"""Parse DPReview product pages."""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from dpreview_scraper.models.camera import Camera
from dpreview_scraper.models.review import ReviewData, ReviewSummary
from dpreview_scraper.models.specs import CameraSpecs
from dpreview_scraper.utils.logging import logger


def parse_product_page(
    overview_html: str,
    specs_html: str,
    review_html: Optional[str],
    product_code: str,
    url: str,
) -> Camera:
    """Parse complete product page.

    Args:
        overview_html: Product overview page HTML
        specs_html: Product specifications page HTML
        review_html: Product review page HTML (optional)
        product_code: Product code
        url: Product URL

    Returns:
        Camera object with all data
    """
    overview_soup = BeautifulSoup(overview_html, "lxml")
    specs_soup = BeautifulSoup(specs_html, "lxml")
    review_soup = BeautifulSoup(review_html, "lxml") if review_html else None

    # Extract top-level metadata from overview page
    name = _extract_name(overview_soup)
    image_url = _extract_image_url(overview_soup)
    short_specs = _extract_short_specs(overview_soup)
    award = _extract_award(overview_soup)

    # Extract full specs from specifications page
    specs = _extract_full_specs(specs_soup)

    # Extract review data from overview and review pages
    review_data, review_score = _extract_review_data(overview_soup, review_soup)

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


def _extract_name(soup: BeautifulSoup) -> str:
    """Extract camera name."""
    # Extract from h1, which contains "[Name] Overview"
    h1 = soup.select_one("h1")
    if h1:
        title = h1.get_text(strip=True)
        # Remove " Overview" suffix if present
        if title.endswith(" Overview"):
            return title[:-9]
        return title

    # Fallback: try breadcrumbs
    breadcrumb = soup.select_one("div.breadcrumbs a.item:last-child")
    if breadcrumb:
        return breadcrumb.get_text(strip=True)

    return ""


def _extract_image_url(soup: BeautifulSoup) -> str:
    """Extract product image URL."""
    # Main product image is in div#productImage with background-image CSS
    product_img_div = soup.select_one("div#productImage")
    if product_img_div:
        style = product_img_div.get("style", "")
        # Extract URL from background-image: url(...)
        match = re.search(r'url\(["\']?([^"\'()]+)["\']?\)', style)
        if match:
            return match.group(1)

    # Fallback: try thumbnail images
    thumbnail = soup.select_one("div.productShotThumbnail")
    if thumbnail:
        style = thumbnail.get("style", "")
        match = re.search(r'url\(["\']?([^"\'()]+)["\']?\)', style)
        if match:
            # This will be a 40x40 thumbnail, but it's better than nothing
            return match.group(1)

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
    """Extract review award (gold, silver, bronze, recommended)."""
    # Awards appear as <span class="award gold/silver/bronze"></span>
    # Usually in sidebar for other products, but check for this product too
    award_elem = soup.select_one("span.award")
    if award_elem:
        classes = award_elem.get("class", [])
        for cls in classes:
            if cls in ["gold", "silver", "bronze"]:
                return cls

    # Check for award in text
    award_text_elem = soup.select_one(".badge, [data-award]")
    if award_text_elem:
        award_text = award_text_elem.get_text(strip=True).lower()
        if "gold" in award_text:
            return "gold"
        elif "silver" in award_text:
            return "silver"
        elif "bronze" in award_text:
            return "bronze"
        elif "recommended" in award_text:
            return "recommended"

    return ""


def _extract_full_specs(soup: BeautifulSoup) -> CameraSpecs:
    """Extract all technical specifications from full specifications page."""
    specs_dict = {}

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
                label_elem = row.select_one("th.label")
                value_elem = row.select_one("td.value")

                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).replace(":", "")
                    value = value_elem.get_text(strip=True)

                    # Map label to spec field
                    field_name = _normalize_spec_name(label)
                    if field_name:
                        # Check if it's a list field
                        if field_name in ["Autofocus", "ExposureModes", "MeteringModes", "FileFormat", "Modes", "DriveModes"]:
                            # Parse as list
                            value_list = _parse_list_value(value_elem)
                            specs_dict[field_name] = value_list
                        else:
                            specs_dict[field_name] = value

            except Exception as e:
                logger.debug(f"Failed to parse spec row: {e}")
                continue

    # Create specs object
    specs = CameraSpecs(**specs_dict)
    return specs


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
        "extended iso": "BoostedISOMaximum",

        # Autofocus
        "autofocus": "Autofocus",
        "af system": "Autofocus",
        "autofocus assist lamp": "AutofocusAssistLamp",
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
        "color space": "ColorSpace",
        "custom white balance": "CustomWhiteBalance",
        "file format": "FileFormat",
        "image ratio w:h": "ImageRatioWh",
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
            text = li.get_text(strip=True)
            if text:
                items.append(text)
    else:
        # Parse comma-separated or line-break separated
        text = elem.get_text()
        # Try splitting by common separators
        for sep in ["\n", ";", ","]:
            if sep in text:
                parts = [p.strip() for p in text.split(sep) if p.strip()]
                if len(parts) > 1:
                    return parts

        # Single item
        if text.strip():
            items.append(text.strip())

    return items


def _parse_review_page(soup: BeautifulSoup) -> tuple:
    """Parse review page content.

    Returns:
        Tuple of (executive_summary, review_summary, review_score)
    """
    executive_summary = ""
    good_for = ""
    not_so_good_for = ""
    conclusion = ""
    review_score = 0

    # Try to extract executive summary from various possible locations
    summary_selectors = [
        "div.article-intro",
        "div.intro",
        "div.summary",
        "div.article p:first-of-type",
    ]

    for selector in summary_selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(strip=True)
            if text and len(text) > 50:  # Ensure it's substantial
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
) -> tuple:
    """Extract review data.

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
            # Extract URL from background-image: url(...)
            match = re.search(r'url\(["\']?([^"\'()]+)["\']?\)', style)
            if match:
                url = match.group(1)
                # Convert thumbnail URL to full size
                # Thumbnail format: TS40x40~products/...
                # Full size format: TS375x375~products/... or larger
                full_url = url.replace("TS40x40", "TS375x375")
                photos.append(full_url)
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

    # Parse review page content if available
    if review_soup:
        executive_summary, review_summary, review_score = _parse_review_page(review_soup)
        review_data.ExecutiveSummary = executive_summary
        review_data.ReviewSummary = review_summary
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
