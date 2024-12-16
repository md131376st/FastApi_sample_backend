import secrets

from fastapi import APIRouter

from .endpoints import subscription, auth, betasignup, google_cloud, ai_agent,dashboard,google_drive, request

api_router = APIRouter()

api_router.include_router(subscription.router, tags=["subscriptions"])
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(betasignup.router, tags=["damo"])

api_router.include_router(google_cloud.router, tags=["Google Cloud"])

api_router.include_router(ai_agent.router, tags=["AI Agent"])

api_router.include_router(dashboard.router, tags=["Dashboard"])

api_router.include_router(google_drive.router, tags=["Google Drive"])

# apis about handling cookies and other browser related information
api_router.include_router(request.router, tags=["config"])