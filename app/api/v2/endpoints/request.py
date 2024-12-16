from fastapi import APIRouter, Response, Request, Query
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


# apis about handling cookies and other browser related information


class CookieRequest(BaseModel):
    key: str
    value: str


class CookieResponse(BaseModel):
    message: str
    cookie_key: str
    cookie_value: str


@router.post("/set-cookie", response_model=CookieResponse)
async def set_cookie(response: Response, cookie: CookieRequest):
    """
    Sets a dynamic cookie on the client's browser.
    """
    response.set_cookie(
        key=cookie.key,
        value=cookie.value,
        httponly=True,
        max_age=3600,  # Cookie expires in 1 hour
        secure=settings.PRODUCTION  # Use True in production for HTTPS
    )
    return {"message": "Cookie has been set", "cookie_key": cookie.key, "cookie_value": cookie.value}


# Endpoint to retrieve a cookie
@router.get("/get-cookie", response_model=CookieResponse)
async def get_cookie(request: Request, key: str = Query(..., description="The key/name of the cookie")):
    """
    Retrieves the cookie from the client's request dynamically by its key.
    """
    cookie_value = request.cookies.get(key)
    if cookie_value:
        return {"message": "Cookie retrieved successfully", "cookie_key": key, "cookie_value": cookie_value}
    return {"message": "Cookie not found", "cookie_key": key, "cookie_value":None}


# Endpoint to delete a cookie
@router.get("/delete-cookie", response_model=CookieResponse)
async def delete_cookie(response: Response):
    """
    Deletes the cookie by setting it with an expired max age.
    """
    response.delete_cookie(key="my_cookie_name")
    return {"message": "Cookie has been deleted", "cookie_value": None}
