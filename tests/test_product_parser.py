"""Tests for product page parsing."""

import pytest

from dpreview_scraper.parsers.product_parser import (
    _extract_clean_url_from_style,
    _extract_name,
    _normalize_spec_name,
    _normalize_whitespace,
    _parse_list_value,
    parse_product_page,
)
from bs4 import BeautifulSoup


class TestExtractCleanUrlFromStyle:
    def test_extracts_url_from_background_image(self):
        style = "background-image: url('https://example.com/img.jpg')"
        assert _extract_clean_url_from_style(style) == "https://example.com/img.jpg"

    def test_removes_size_parameters(self):
        style = "background-image: url('https://example.com/TS375x375~img.jpg')"
        assert _extract_clean_url_from_style(style) == "https://example.com/img.jpg"

    def test_no_url_returns_empty(self):
        assert _extract_clean_url_from_style("color: red") == ""

    def test_handles_double_quotes(self):
        style = 'background-image: url("https://example.com/img.jpg")'
        assert _extract_clean_url_from_style(style) == "https://example.com/img.jpg"

    def test_handles_no_quotes(self):
        style = "background-image: url(https://example.com/img.jpg)"
        assert _extract_clean_url_from_style(style) == "https://example.com/img.jpg"


class TestExtractName:
    def test_extracts_name_from_h1(self):
        html = "<html><body><h1>Sony a7 V Overview</h1></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_name(soup) == "Sony a7 V"

    def test_removes_overview_suffix(self):
        html = "<html><body><h1>Canon EOS R5 Overview</h1></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_name(soup) == "Canon EOS R5"

    def test_returns_full_h1_without_suffix(self):
        html = "<html><body><h1>Just a title</h1></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_name(soup) == "Just a title"

    def test_returns_empty_when_no_h1(self):
        html = "<html><body><p>No heading</p></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _extract_name(soup) == ""

    def test_extracts_from_real_fixture(self, product_overview_html):
        soup = BeautifulSoup(product_overview_html, "lxml")
        name = _extract_name(soup)
        assert "Sony" in name
        assert "a7 V" in name or "a7V" in name


class TestNormalizeSpecName:
    def test_maps_known_labels(self):
        assert _normalize_spec_name("Body type") == "BodyType"
        assert _normalize_spec_name("Sensor type") == "SensorType"
        assert _normalize_spec_name("Effective pixels") == "EffectivePixels"
        assert _normalize_spec_name("MSRP") == "MSRP"

    def test_case_insensitive(self):
        assert _normalize_spec_name("BODY TYPE") == "BodyType"
        assert _normalize_spec_name("sensor type") == "SensorType"

    def test_returns_none_for_unknown(self):
        assert _normalize_spec_name("Unknown Spec Label") is None

    def test_handles_whitespace(self):
        assert _normalize_spec_name("  Body type  ") == "BodyType"

    def test_maps_alternative_names(self):
        assert _normalize_spec_name("megapixels") == "EffectivePixels"
        assert _normalize_spec_name("crop factor") == "FocalLengthMultiplier"
        assert _normalize_spec_name("wifi") == "Wireless"


class TestNormalizeWhitespace:
    def test_collapses_spaces(self):
        assert _normalize_whitespace("a   b") == "a b"

    def test_removes_space_before_inch(self):
        assert _normalize_whitespace('3.0 ″') == '3.0″'


class TestParseListValue:
    def test_parses_ul_list(self):
        html = "<td><ul><li>Item 1</li><li>Item 2</li></ul></td>"
        elem = BeautifulSoup(html, "lxml").find("td")
        result = _parse_list_value(elem)
        assert result == ["Item 1", "Item 2"]

    def test_parses_comma_separated(self):
        html = "<td>Item 1, Item 2, Item 3</td>"
        elem = BeautifulSoup(html, "lxml").find("td")
        result = _parse_list_value(elem)
        assert len(result) == 3

    def test_single_value(self):
        html = "<td>Single item</td>"
        elem = BeautifulSoup(html, "lxml").find("td")
        result = _parse_list_value(elem)
        assert result == ["Single item"]


class TestParseProductPage:
    def test_parses_from_fixtures(self, product_overview_html, product_specs_html):
        camera = parse_product_page(
            overview_html=product_overview_html,
            specs_html=product_specs_html,
            review_html=None,
            review_specs_html=None,
            product_code="sony_a7v",
            url="/products/sony/slrs/sony_a7v",
        )
        assert camera.ProductCode == "sony_a7v"
        assert camera.URL == "/products/sony/slrs/sony_a7v"

    def test_extracts_name_from_overview(self, product_overview_html, product_specs_html):
        camera = parse_product_page(
            overview_html=product_overview_html,
            specs_html=product_specs_html,
            review_html=None,
            review_specs_html=None,
            product_code="sony_a7v",
            url="/products/sony/slrs/sony_a7v",
        )
        assert "Sony" in camera.Name

    def test_extracts_specs(self, product_overview_html, product_specs_html):
        camera = parse_product_page(
            overview_html=product_overview_html,
            specs_html=product_specs_html,
            review_html=None,
            review_specs_html=None,
            product_code="sony_a7v",
            url="/products/sony/slrs/sony_a7v",
        )
        # Sony a7 V specs page should have body type and sensor info
        assert camera.Specs.BodyType or camera.Specs.SensorType or camera.Specs.MSRP

    def test_uses_provided_short_specs(self, product_overview_html, product_specs_html):
        short_specs = ["33 megapixels", '3.2″ screen', "Full frame sensor"]
        camera = parse_product_page(
            overview_html=product_overview_html,
            specs_html=product_specs_html,
            review_html=None,
            review_specs_html=None,
            product_code="sony_a7v",
            url="/products/sony/slrs/sony_a7v",
            short_specs=short_specs,
        )
        assert camera.ShortSpecs == short_specs

    def test_review_data_present_without_review(self, product_overview_html, product_specs_html):
        camera = parse_product_page(
            overview_html=product_overview_html,
            specs_html=product_specs_html,
            review_html=None,
            review_specs_html=None,
            product_code="sony_a7v",
            url="/products/sony/slrs/sony_a7v",
        )
        # ReviewData should exist even without a review page
        assert camera.ReviewData is not None
        assert camera.ReviewScore >= 0
