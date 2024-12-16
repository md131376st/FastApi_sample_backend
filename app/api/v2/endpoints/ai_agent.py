from fastapi import APIRouter, HTTPException, Request

from pydantic import BaseModel

from app.services.ai_service import process_ai_response, process_ai_response_text

router = APIRouter()


class UserMessage(BaseModel):
    companyId: str
    userId: str
    lang: str
    wavData: str  # Base64 encoded data for audio
    # class Config:
    #     json_encoders = {ObjectId: str}
    #     populate_by_name = True
    #     arbitrary_types_allowed = True


@router.post("/usermessage")
async def store_user_messages(request: Request, input: UserMessage):
    try:
        # Call the service that processes the user message and AI interaction
        ai_response = await process_ai_response(input)
        return ai_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UserMessageText(BaseModel):
    companyId: str
    userId: str
    lang: str
    question: str
    # class Config:
    #     json_encoders = {ObjectId: str}
    #     populate_by_name = True
    #     arbitrary_types_allowed = True


@router.post("/textusermessage")
async def store_user_messages_text(request: Request, input: UserMessageText):
    try:
        # Call the service that processes the text message and AI interaction
        ai_response = await process_ai_response_text(input)
        return ai_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
