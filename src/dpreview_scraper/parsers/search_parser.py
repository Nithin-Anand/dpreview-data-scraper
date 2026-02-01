"""Parse DPReview search results."""

from typing import List
from bs4 import BeautifulSoup

from dpreview_scraper.models.camera import SearchResult
from dpreview_scraper.utils.logging import logger


def parse_search_results(html: str) -> List[SearchResult]:
    """Parse camera search results from HTML.

    Args:
        html: Search results page HTML

    Returns:
        List of search results
    """
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Find product rows in the table
    # Structure: <tr id="product_[code]" class="product">
    product_elements = soup.select("tr.product")

    if not product_elements:
        logger.warning("No product elements found in search results")
        return results

    for element in product_elements:
        try:
            # Extract product code from id attribute (e.g., "product_sony_a7v")
            product_id = element.get("id", "")
            if product_id.startswith("product_"):
                product_code = product_id.replace("product_", "")
            else:
                # Fallback: extract from URL
                link = element.select_one("td.info div.name a")
                if not link:
                    continue
                url = link.get("href", "")
                if not url:
                    continue
                parts = url.strip("/").split("/")
                if len(parts) < 3:
                    continue
                product_code = parts[-1]

            # Extract URL from name link
            link = element.select_one("td.info div.name a")
            if not link:
                continue

            url = link.get("href", "")
            if not url:
                continue

            # Extract name
            name = link.get_text(strip=True)

            # Extract image
            img = element.select_one("td.product div.productImage a img")
            image_url = img.get("src", "") if img else ""

            # Extract announcement date
            announced = None
            date_elem = element.select_one("td.info div.announcementDate")
            if date_elem:
                announced = date_elem.get_text(strip=True)

            result = SearchResult(
                product_code=product_code,
                name=name,
                url=url,
                image_url=image_url,
                announced=announced,
            )
            results.append(result)
            logger.debug(f"Parsed search result: {product_code}")

        except Exception as e:
            logger.warning(f"Failed to parse search result: {e}")
            continue

    logger.info(f"Parsed {len(results)} search results")
    return results


def extract_pagination_info(html: str) -> dict:
    """Extract pagination information.

    Args:
        html: Search results page HTML

    Returns:
        Dict with pagination info (current_page, total_pages, has_next)
    """
    soup = BeautifulSoup(html, "lxml")

    info = {
        "current_page": 1,
        "total_pages": 1,
        "has_next": False,
    }

    try:
        # Check for next page link in HTML head
        next_link = soup.select_one('link[rel="next"]')
        if next_link:
            info["has_next"] = True
            next_href = next_link.get("href", "")
            # Try to extract page number from URL
            if "page=" in next_href:
                try:
                    page_param = next_href.split("page=")[1].split("&")[0]
                    next_page = int(page_param)
                    info["current_page"] = next_page - 1
                except (ValueError, IndexError):
                    pass

        # Look for pagination in table.pager or table.pages
        pagination = soup.select_one("table.pager, table.pages")
        if pagination:
            # Current page
            current = pagination.select_one(".active, .current, [aria-current='page']")
            if current:
                try:
                    info["current_page"] = int(current.get_text(strip=True))
                except ValueError:
                    pass

            # Total pages from page links
            page_links = pagination.select("a")
            if page_links:
                page_numbers = []
                for link in page_links:
                    try:
                        num = int(link.get_text(strip=True))
                        page_numbers.append(num)
                    except ValueError:
                        continue
                if page_numbers:
                    info["total_pages"] = max(page_numbers)

    except Exception as e:
        logger.warning(f"Failed to parse pagination: {e}")

    return info
