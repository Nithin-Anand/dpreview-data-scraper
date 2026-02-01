"""Review data models."""

from typing import List
from pydantic import BaseModel, Field


class ReviewSummary(BaseModel):
    """Review summary with pros, cons, and conclusion."""

    GoodFor: str = ""
    NotSoGoodFor: str = ""
    Conclusion: str = ""


# Create an alias to avoid name collision during class definition
_ReviewSummaryType = ReviewSummary


class ReviewData(BaseModel):
    """Complete review data including summary and media."""

    ExecutiveSummary: str = ""
    ProductPhotos: List[str] = Field(default_factory=list)
    ReviewSummary: _ReviewSummaryType = Field(default_factory=_ReviewSummaryType)
    ASIN: List[str] = Field(default_factory=list)
