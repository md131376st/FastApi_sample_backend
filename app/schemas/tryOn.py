from pydantic import BaseModel, field_validator, ConfigDict
from typing import Annotated, Optional, Literal, List


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


class Question(BaseModel):
    id: int
    question: str
    choices: List[str]


class UserAnswerResponse(BaseModel):
    message: str
    id: str
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Answers stored successfully",
                "id": "65fa1234567e89abc0123456",
                "user_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )
