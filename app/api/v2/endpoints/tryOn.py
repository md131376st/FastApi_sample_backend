import json
from typing import List
from uuid import uuid4

from fastapi import status, APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.database import get_db
from app.models.tryOn import UserAnswer
from app.schemas.tryOn import Question, UserAnswerResponse
from app.services.gcs_service import get_file_from_gcs

router = APIRouter()


@router.get("/questions", response_model=List[Question])
async def get_questions():
    try:

        json_path = f"{settings.GCS_DOCUMENT_PATH}/questions.json"
        json_content = get_file_from_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=json_path, as_text=True)
        questions_data = json.loads(json_content)

        return questions_data.get("questions", [])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Questions file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to decode JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/questions", response_model=UserAnswerResponse)
async def store_answers(user_answer: UserAnswer, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        collection = db.get_collection("tryOn")
        if not user_answer.user_id:
            user_answer.user_id = str(uuid4())
        user_answer_dict = user_answer.model_dump()
        # Insert into MongoDB
        result = await collection.insert_one(user_answer_dict)

        return {
            "message": "Answers stored successfully",
            "id": str(result.inserted_id),
            "user_id": user_answer.user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
