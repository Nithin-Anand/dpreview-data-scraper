"""Tests for data models and YAML serialization."""

from dpreview_scraper.models.camera import Camera, SearchResult
from dpreview_scraper.models.review import ReviewData, ReviewSummary
from dpreview_scraper.models.specs import CameraSpecs


class TestSearchResult:
    def test_create_minimal(self):
        result = SearchResult(
            product_code="sony_a7v",
            name="Sony a7 V",
            url="/products/sony/slrs/sony_a7v",
        )
        assert result.product_code == "sony_a7v"
        assert result.image_url == ""
        assert result.short_specs == []
        assert result.announced is None

    def test_create_full(self):
        result = SearchResult(
            product_code="sony_a7v",
            name="Sony a7 V",
            url="/products/sony/slrs/sony_a7v",
            image_url="/files/p/products/sony_a7v/hero.jpg",
            announced="Oct 2024",
            short_specs=["33 megapixels", "Full frame"],
        )
        assert result.announced == "Oct 2024"
        assert len(result.short_specs) == 2


class TestCameraSpecs:
    def test_defaults_to_empty_strings(self):
        specs = CameraSpecs()
        assert specs.BodyType == ""
        assert specs.SensorType == ""
        assert specs.ISO == ""

    def test_list_fields_default_to_empty(self):
        specs = CameraSpecs()
        assert specs.Autofocus == []
        assert specs.ExposureModes == []
        assert specs.FileFormat == []

    def test_allows_extra_fields(self):
        specs = CameraSpecs(UnknownField="some value")
        assert specs.model_dump()["UnknownField"] == "some value"

    def test_model_dump_includes_all_fields(self):
        specs = CameraSpecs(BodyType="Mirrorless", SensorSize="Full frame")
        data = specs.model_dump()
        assert data["BodyType"] == "Mirrorless"
        assert data["SensorSize"] == "Full frame"
        assert "ISO" in data  # empty fields still present


class TestReviewData:
    def test_defaults(self):
        rd = ReviewData()
        assert rd.ExecutiveSummary == ""
        assert rd.ProductPhotos == []
        assert rd.ASIN == []
        assert rd.ReviewSummary.GoodFor == ""

    def test_with_data(self):
        rd = ReviewData(
            ExecutiveSummary="Great camera",
            ProductPhotos=["/img1.jpg", "/img2.jpg"],
            ReviewSummary=ReviewSummary(
                GoodFor="Everything",
                NotSoGoodFor="Price",
                Conclusion="Buy it",
            ),
            ASIN=["B0123456"],
        )
        assert rd.ExecutiveSummary == "Great camera"
        assert len(rd.ProductPhotos) == 2
        assert rd.ReviewSummary.GoodFor == "Everything"


class TestCamera:
    def _make_camera(self, **overrides):
        defaults = dict(
            ProductCode="sony_a7v",
            Name="Sony a7 V",
            URL="/products/sony/slrs/sony_a7v",
        )
        defaults.update(overrides)
        return Camera(**defaults)

    def test_create_minimal(self):
        camera = self._make_camera()
        assert camera.ProductCode == "sony_a7v"
        assert camera.ReviewScore == 0
        assert camera.Award == ""

    def test_to_yaml_dict_has_expected_keys(self):
        camera = self._make_camera()
        data = camera.to_yaml_dict()
        expected_keys = [
            "DPRReviewArchiveURL",
            "ProductCode",
            "Award",
            "ImageURL",
            "Name",
            "ShortSpecs",
            "ReviewScore",
            "URL",
            "ReviewData",
            "Specs",
        ]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def test_to_yaml_dict_strips_domains(self):
        camera = self._make_camera(
            ImageURL="https://1.img-dpreview.com/files/p/products/sony_a7v/hero.jpg",
        )
        data = camera.to_yaml_dict()
        assert data["ImageURL"].startswith("/files/p/products/")
        assert "img-dpreview.com" not in data["ImageURL"]

    def test_to_yaml_dict_removes_size_params(self):
        camera = self._make_camera(
            ImageURL="https://1.img-dpreview.com/files/p/TS375x375~products/sony_a7v/hero.jpg",
        )
        data = camera.to_yaml_dict()
        assert "TS375x375~" not in data["ImageURL"]

    def test_to_yaml_dict_review_data_structure(self):
        camera = self._make_camera()
        data = camera.to_yaml_dict()
        rd = data["ReviewData"]
        assert "ExecutiveSummary" in rd
        assert "ProductPhotos" in rd
        assert "ReviewSummary" in rd
        assert "ASIN" in rd

    def test_to_yaml_dict_specs_sorted(self):
        camera = self._make_camera(
            Specs=CameraSpecs(BodyType="Mirrorless", Announced="2024"),
        )
        data = camera.to_yaml_dict()
        spec_keys = list(data["Specs"].keys())
        assert spec_keys == sorted(spec_keys)

    def test_review_summary_none_when_empty(self):
        camera = self._make_camera()
        data = camera.to_yaml_dict()
        # When all review summary fields are empty, should be None
        assert data["ReviewData"]["ReviewSummary"] is None

    def test_review_summary_present_when_populated(self):
        camera = self._make_camera(
            ReviewData=ReviewData(
                ReviewSummary=ReviewSummary(
                    GoodFor="Great AF",
                    NotSoGoodFor="Battery",
                    Conclusion="Recommended",
                ),
            ),
        )
        data = camera.to_yaml_dict()
        rs = data["ReviewData"]["ReviewSummary"]
        assert rs is not None
        assert rs["GoodFor"] == "Great AF"

    def test_excludes_internal_fields(self):
        camera = self._make_camera()
        camera.review_url = "https://dpreview.com/reviews/sony-a7v"
        data = camera.to_yaml_dict()
        assert "review_url" not in data
