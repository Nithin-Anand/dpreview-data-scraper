"""Extract technical specifications from product and review pages."""

import re
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from dpreview_scraper.models.specs import CameraSpecs
from dpreview_scraper.parsers.parse_utils import normalize_whitespace
from dpreview_scraper.utils.logging import logger

ANNOUNCED_PREFIX_PATTERN = re.compile(r'^Announced\s+')

# Fields that should be parsed as lists
LIST_SPEC_FIELDS = frozenset({
    "Autofocus", "ExposureModes", "MeteringModes",
    "FileFormat", "Modes", "DriveModes"
})

# Mapping of HTML label text -> CameraSpecs field name
SPEC_LABEL_MAPPING = {
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


def normalize_spec_name(label: str) -> Optional[str]:
    """Normalize spec label to CameraSpecs field name.

    Args:
        label: HTML label text (e.g., "Body type", "Sensor size")

    Returns:
        CameraSpecs field name or None if label is unmapped
    """
    return SPEC_LABEL_MAPPING.get(label.lower().strip())


def parse_list_value(elem: Tag) -> List[str]:
    """Parse an HTML element value that should be a list.

    Handles <ul>/<ol> lists and comma/semicolon/newline-separated text.
    """
    items = []

    ul = elem.find("ul") or elem.find("ol")
    if ul:
        for li in ul.find_all("li"):
            text = normalize_whitespace(li.get_text(separator=' ', strip=True))
            if text:
                items.append(text)
    else:
        text = normalize_whitespace(elem.get_text(separator=' ', strip=True))
        for sep in ["\n", ";", ","]:
            if sep in text:
                parts = [normalize_whitespace(p) for p in text.split(sep) if p.strip()]
                if len(parts) > 1:
                    return parts

        if text.strip():
            items.append(text.strip())

    return items


def _parse_spec_row(
    row: Tag,
    label_selector: str,
    value_selector: str
) -> Optional[tuple[str, str | list]]:
    """Parse a single spec row, returning (field_name, value) or None."""
    label_elem = row.select_one(label_selector)
    value_elem = row.select_one(value_selector)

    if not label_elem or not value_elem:
        return None

    label = label_elem.get_text(strip=True).replace(":", "")
    value = normalize_whitespace(value_elem.get_text(separator=' ', strip=True))

    if not value:
        return None

    field_name = normalize_spec_name(label)
    if not field_name:
        logger.debug(f"UNMAPPED LABEL: '{label}' = '{value[:50] if len(value) > 50 else value}'")
        return None

    if field_name in LIST_SPEC_FIELDS:
        return (field_name, parse_list_value(value_elem))

    if field_name == "Announced":
        value = ANNOUNCED_PREFIX_PATTERN.sub('', value)

    return (field_name, value)


def extract_review_specs(soup: BeautifulSoup) -> CameraSpecs:
    """Extract specs from review page 2 (table.contentTable).

    Review specs pages have more comprehensive data than the regular specs page.
    """
    specs_dict: dict[str, str | list] = {}

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


def merge_specs(primary: CameraSpecs, secondary: CameraSpecs) -> CameraSpecs:
    """Merge two CameraSpecs, using primary values and filling gaps from secondary."""
    merged_dict = {}

    for field_name in primary.model_fields:
        primary_value = getattr(primary, field_name)
        secondary_value = getattr(secondary, field_name)

        if primary_value:
            if isinstance(primary_value, list):
                merged_dict[field_name] = primary_value if primary_value else secondary_value
            else:
                merged_dict[field_name] = primary_value
        else:
            merged_dict[field_name] = secondary_value

    return CameraSpecs(**merged_dict)


def extract_full_specs(soup: BeautifulSoup) -> CameraSpecs:
    """Extract all technical specifications from full specifications page."""
    specs_dict: dict[str, str | list] = {}

    specs_table = soup.select_one("table.specsTable.compact")
    if not specs_table:
        logger.warning("No specifications table found")
        return CameraSpecs(**specs_dict)

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
