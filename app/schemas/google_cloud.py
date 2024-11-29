from pydantic import BaseModel
from typing import List, Optional, Dict


class Coordinate(BaseModel):
    x: float
    y: float
    z: float
    image: List[str]
    description: Optional[str]

class Image(BaseModel):
    id: int
    image: str
    coordinates: List[Coordinate]

class Project(BaseModel):
    projectName: str
    images: List[Image]
    charecter: str

class ProjectList(BaseModel):
    projects: List[Project]

class ImageBase64Response(BaseModel):
    image_base64: str

class RecommendationList(BaseModel):
    image_paths: Dict[str, List[str]]