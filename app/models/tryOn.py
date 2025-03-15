from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict


class UserAnswer(BaseModel):
    user_id: Optional[str] = None
    answers: List[
        dict]  # Example: [{"question_id": 1, "answer": "Casual"}, {"question_id": 2, "answer": "Everyday wear"}]
    model_config = ConfigDict(
        populate_by_name=True,  # Allows alias mapping (_id ↔ user_id)
        arbitrary_types_allowed=True,  # Allows handling of non-Pydantic types (e.g., ObjectId)
        json_encoders={ObjectId: str},  # Ensures MongoDB ObjectId is encoded as a string
        json_schema_extra={  # Example for API docs
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "answers": [
                    {"question_id": 1, "answer": "Casual"},
                    {"question_id": 2, "answer": "Everyday wear"}
                ]
            }
        }
    )
