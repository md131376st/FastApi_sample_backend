from pydantic import BaseModel, field_validator
from typing import Annotated, Optional, Literal


class NewCharacter(BaseModel):
    projectName: str
    character: str
    image: str


# Request Model
class TryOnRequest(BaseModel):
    # Required parameters

    # Quality control parameters
    guidance_scale: Annotated[float, (1.5, 3.0)] = 2.0  # Range: 1.5-3.0
    timesteps: Annotated[int, (10, 50)] = 50  # Range: 10-50
    num_samples: Annotated[int, (1, 4)] = 1  # Range: 1-4

    # Seed for reproducibility
    seed: Optional[int] = 42  # Any integer is allowed

    # Image processing options
    nsfw_filter: Optional[bool] = True
    cover_feet: Optional[bool] = False
    adjust_hands: Optional[bool] = False
    restore_background: Optional[bool] = False
    restore_clothes: Optional[bool] = False

    # Garment-specific options
    garment_photo_type: Annotated[
        str,
        Literal["auto", "flat-lay", "model"]
    ] = "auto"  # Allowed values: 'auto', 'flat-lay', 'model'
    long_top: Optional[bool] = False

