"""Shared parsing utilities."""

import re

# Precompiled regex patterns
URL_FROM_CSS_PATTERN = re.compile(r'url\(["\']?([^"\'()]+)["\']?\)')
DPREVIEW_SIZE_PARAM_PATTERN = re.compile(r'TS\d+x\d+~')
MULTIPLE_SPACES_PATTERN = re.compile(r'\s+')
SPACE_BEFORE_INCH_PATTERN = re.compile(r'\s+(″|"|\'\'|")')
SPACE_BEFORE_PAREN_PATTERN = re.compile(r'\s+\)')


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text by collapsing multiple spaces to single space.

    Also removes spaces before inch symbols and closing parentheses.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    text = MULTIPLE_SPACES_PATTERN.sub(' ', text)
    text = SPACE_BEFORE_INCH_PATTERN.sub(r'\1', text)
    text = SPACE_BEFORE_PAREN_PATTERN.sub(')', text)
    return text.strip()


def extract_clean_url_from_style(style: str) -> str:
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
