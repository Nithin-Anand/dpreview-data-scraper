"""Tests for search result parsing."""

from dpreview_scraper.parsers.search_parser import (
    _normalize_whitespace,
    extract_pagination_info,
    parse_search_results,
)


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self):
        assert _normalize_whitespace("hello   world") == "hello world"

    def test_strips_leading_trailing(self):
        assert _normalize_whitespace("  hello  ") == "hello"

    def test_removes_space_before_inch_symbol(self):
        assert _normalize_whitespace('3 ″ screen') == '3″ screen'

    def test_removes_space_before_closing_paren(self):
        assert _normalize_whitespace("APS-C (1.5x )") == "APS-C (1.5x)"

    def test_empty_string(self):
        assert _normalize_whitespace("") == ""


class TestParseSearchResults:
    def test_parses_products_from_fixture(self, camera_list_html):
        results = parse_search_results(camera_list_html)
        assert len(results) > 0

    def test_product_has_required_fields(self, camera_list_html):
        results = parse_search_results(camera_list_html)
        first = results[0]
        assert first.product_code
        assert first.name
        assert first.url

    def test_empty_html_returns_empty(self):
        results = parse_search_results("<html><body></body></html>")
        assert results == []

    def test_no_product_rows_returns_empty(self):
        html = "<html><body><table><tr><td>Not a product</td></tr></table></body></html>"
        results = parse_search_results(html)
        assert results == []


class TestExtractPaginationInfo:
    def test_detects_next_page(self, camera_list_html):
        info = extract_pagination_info(camera_list_html)
        assert info["has_next"] is True

    def test_extracts_current_page(self, camera_list_html):
        info = extract_pagination_info(camera_list_html)
        assert info["current_page"] >= 1

    def test_empty_html_defaults(self):
        info = extract_pagination_info("<html><body></body></html>")
        assert info["current_page"] == 1
        assert info["total_pages"] == 1
        assert info["has_next"] is False
