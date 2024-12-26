from fastapi import  status, APIRouter

from app.core.config import settings
from app.schemas.tryOn import TryOnRequest, NewCharacter

router = APIRouter()


@router.post("/try-on-ai-call", status_code=status.HTTP_200_OK)
async def try_on(request: TryOnRequest):

    # Placeholder for processing logic
    return {
        "status": "success",
        "message": "Processing complete.",
        "parameters_used": request.model_dump()
    }



