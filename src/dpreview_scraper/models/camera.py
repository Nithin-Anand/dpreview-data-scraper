"""Camera model combining all data."""

from typing import List, Optional
from pydantic import BaseModel, Field

from dpreview_scraper.models.review import ReviewData
from dpreview_scraper.models.specs import CameraSpecs

# Create aliases to avoid name collisions
_ReviewDataType = ReviewData
_CameraSpecsType = CameraSpecs


class SearchResult(BaseModel):
    """Camera search result from the product search page."""

    product_code: str
    name: str
    url: str
    image_url: str = ""
    announced: Optional[str] = None
    short_specs: List[str] = Field(default_factory=list)


class Camera(BaseModel):
    """Complete camera data matching DPReview YAML schema."""

    # Top-level metadata (order matters for YAML output)
    DPRReviewArchiveURL: str = ""
    ProductCode: str
    Award: str = ""
    ImageURL: str = ""
    Name: str
    ShortSpecs: List[str] = Field(default_factory=list)
    ReviewScore: int = 0
    URL: str
    ReviewData: _ReviewDataType = Field(default_factory=_ReviewDataType)
    Specs: _CameraSpecsType = Field(default_factory=_CameraSpecsType)

    # Internal fields (not written to YAML)
    review_url: Optional[str] = Field(default=None, exclude=True)

    def _format_review_summary(self) -> Optional[dict]:
        """Format ReviewSummary, returning None if all fields are empty."""
        good_for = self.ReviewData.ReviewSummary.GoodFor
        not_so_good_for = self.ReviewData.ReviewSummary.NotSoGoodFor
        conclusion = self.ReviewData.ReviewSummary.Conclusion

        # If all fields are empty, return None (will be written as 'null' in YAML)
        if not good_for and not not_so_good_for and not conclusion:
            return None

        return {
            "GoodFor": good_for,
            "NotSoGoodFor": not_so_good_for,
            "Conclusion": conclusion,
        }

    def to_yaml_dict(self) -> dict:
        """Convert to dict preserving field order for YAML output."""
        import re

        def make_relative_url(url: str) -> str:
            """Convert absolute URL to relative path and remove size parameters."""
            if not url:
                return url
            # Strip domain from DPReview URLs
            for domain in [
                "https://www.dpreview.com",
                "https://m.dpreview.com",
                "https://1.img-dpreview.com",
                "https://2.img-dpreview.com",
                "https://3.img-dpreview.com",
                "https://4.img-dpreview.com",
            ]:
                if url.startswith(domain):
                    url = url[len(domain):]
                    break
            # Remove thumbnail size parameters (e.g., TS375x375~, TS40x40~)
            url = re.sub(r'TS\d+x\d+~', '', url)
            return url

        data = {
            "DPRReviewArchiveURL": self.DPRReviewArchiveURL,
            "ProductCode": self.ProductCode,
            "Award": self.Award,
            "ImageURL": make_relative_url(self.ImageURL),
            "Name": self.Name,
            "ShortSpecs": self.ShortSpecs,
            "ReviewScore": self.ReviewScore,
            "URL": make_relative_url(self.URL),
            "ReviewData": {
                "ExecutiveSummary": self.ReviewData.ExecutiveSummary,
                "ProductPhotos": [make_relative_url(p) for p in self.ReviewData.ProductPhotos],
                "ReviewSummary": self._format_review_summary(),
                "ASIN": self.ReviewData.ASIN,
            },
            "Specs": dict(sorted(self.Specs.model_dump(exclude_none=False).items())),
        }
        return data
