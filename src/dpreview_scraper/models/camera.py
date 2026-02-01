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

    def to_yaml_dict(self) -> dict:
        """Convert to dict preserving field order for YAML output."""
        data = {
            "DPRReviewArchiveURL": self.DPRReviewArchiveURL,
            "ProductCode": self.ProductCode,
            "Award": self.Award,
            "ImageURL": self.ImageURL,
            "Name": self.Name,
            "ShortSpecs": self.ShortSpecs,
            "ReviewScore": self.ReviewScore,
            "URL": self.URL,
            "ReviewData": {
                "ExecutiveSummary": self.ReviewData.ExecutiveSummary,
                "ProductPhotos": self.ReviewData.ProductPhotos,
                "ReviewSummary": {
                    "GoodFor": self.ReviewData.ReviewSummary.GoodFor,
                    "NotSoGoodFor": self.ReviewData.ReviewSummary.NotSoGoodFor,
                    "Conclusion": self.ReviewData.ReviewSummary.Conclusion,
                },
                "ASIN": self.ReviewData.ASIN,
            },
            "Specs": self.Specs.model_dump(exclude_none=False),
        }
        return data
