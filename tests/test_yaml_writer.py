"""Tests for YAML output writer."""

import yaml
from pathlib import Path

import pytest

from dpreview_scraper.models.camera import Camera
from dpreview_scraper.models.review import ReviewData, ReviewSummary
from dpreview_scraper.models.specs import CameraSpecs
from dpreview_scraper.storage.yaml_writer import CustomDumper, YAMLWriter


class TestCustomDumper:
    def test_multiline_strings_use_literal_style(self):
        data = {"text": "line one\nline two\nline three"}
        output = yaml.dump(data, Dumper=CustomDumper, default_flow_style=False)
        assert "|" in output

    def test_empty_strings_use_double_quotes(self):
        data = {"field": ""}
        output = yaml.dump(data, Dumper=CustomDumper, default_flow_style=False)
        assert '""' in output

    def test_numeric_strings_use_double_quotes(self):
        data = {"value": "42"}
        output = yaml.dump(data, Dumper=CustomDumper, default_flow_style=False)
        assert '"42"' in output

    def test_yaml_keywords_use_double_quotes(self):
        for keyword in ["yes", "no", "true", "false", "null"]:
            data = {"field": keyword}
            output = yaml.dump(data, Dumper=CustomDumper, default_flow_style=False)
            assert f'"{keyword}"' in output

    def test_long_strings_use_single_quotes(self):
        long_text = "A" * 150
        data = {"field": long_text}
        output = yaml.dump(data, Dumper=CustomDumper, default_flow_style=False)
        assert "'" in output

    def test_empty_list_representation(self):
        data = {"items": []}
        output = yaml.dump(data, Dumper=CustomDumper, default_flow_style=False)
        assert "[]" in output


class TestYAMLWriter:
    def test_write_camera_creates_file(self, tmp_path):
        writer = YAMLWriter(tmp_path)
        camera = Camera(
            ProductCode="test_camera",
            Name="Test Camera",
            URL="/products/test/test_camera",
        )
        filepath = writer.write_camera(camera)
        assert filepath.exists()
        assert filepath.name == "test_camera.yaml"

    def test_write_camera_valid_yaml(self, tmp_path):
        writer = YAMLWriter(tmp_path)
        camera = Camera(
            ProductCode="test_camera",
            Name="Test Camera",
            URL="/products/test/test_camera",
            ReviewScore=85,
            Award="gold",
            ShortSpecs=["33 megapixels", "Full frame"],
        )
        filepath = writer.write_camera(camera)
        # Verify it's valid YAML that can be loaded back
        with open(filepath) as f:
            data = yaml.safe_load(f)
        assert data["ProductCode"] == "test_camera"
        assert data["ReviewScore"] == 85
        assert data["ShortSpecs"] == ["33 megapixels", "Full frame"]

    def test_camera_exists(self, tmp_path):
        writer = YAMLWriter(tmp_path)
        assert not writer.camera_exists("test_camera")

        camera = Camera(
            ProductCode="test_camera",
            Name="Test Camera",
            URL="/products/test/test_camera",
        )
        writer.write_camera(camera)
        assert writer.camera_exists("test_camera")

    def test_creates_output_directory(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        writer = YAMLWriter(nested)
        assert nested.exists()

    def test_round_trip_preserves_data(self, tmp_path):
        writer = YAMLWriter(tmp_path)
        camera = Camera(
            ProductCode="round_trip",
            Name="Round Trip Camera",
            URL="/products/test/round_trip",
            ReviewScore=92,
            Award="gold",
            ShortSpecs=["50 megapixels"],
            ReviewData=ReviewData(
                ExecutiveSummary="A great camera for professionals.",
                ProductPhotos=["/img1.jpg", "/img2.jpg"],
                ReviewSummary=ReviewSummary(
                    GoodFor="Portrait photography",
                    NotSoGoodFor="Video",
                    Conclusion="Highly recommended",
                ),
                ASIN=["B0123"],
            ),
            Specs=CameraSpecs(
                BodyType="Mirrorless",
                SensorType="BSI-CMOS",
                EffectivePixels="50 megapixels",
            ),
        )
        filepath = writer.write_camera(camera)

        with open(filepath) as f:
            data = yaml.safe_load(f)

        assert data["Name"] == "Round Trip Camera"
        assert data["ReviewScore"] == 92
        assert data["ReviewData"]["ExecutiveSummary"] == "A great camera for professionals."
        assert data["ReviewData"]["ReviewSummary"]["GoodFor"] == "Portrait photography"
        assert data["Specs"]["BodyType"] == "Mirrorless"
