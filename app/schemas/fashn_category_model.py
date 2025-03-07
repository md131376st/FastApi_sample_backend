from pydantic import BaseModel, Field
from app.core.enums import FashnCategory
from typing import Dict, List, Optional


class FashnCategoryModel(BaseModel):
    """
    Base model for Fashn categories.
    Ensures a structured format for storing garments per category.
    """
    categories: Dict[FashnCategory, List[str]] = Field(
        default_factory=lambda: {
            FashnCategory.TOPS: [],
            FashnCategory.BOTTOMS: [],
            FashnCategory.OVERWEARS: [],
            FashnCategory.FULLBODYS: []
        }
    )

    def add_garment(self, category: FashnCategory, garment_name: str):
        """Adds a garment to the specified category."""
        if category not in self.categories:
            raise ValueError(f"Invalid category '{category.value}'. Must be one of {FashnCategory.list()}.")
        self.categories[category].append(garment_name)

class ClothItem(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    diversity_weight: Optional[float] = 0.3