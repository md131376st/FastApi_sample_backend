from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.v2.router import api_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, close_db
from app.google_drive import close_google_drive, init_google_drive
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Allowed origins for CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://www.morseverse.com",
    "https://morseverse.com/ai_agent",
    "https://accounts.google.com"
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize resources during startup
        logger.info("Initializing resources...")
        await init_db()
        await init_google_drive()
        logger.info("Resources initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise e
    finally:
        # Clean up resources during shutdown
        logger.info("Shutting down resources...")
        await close_google_drive()
        await close_db()
        logger.info("Resources shut down successfully")



# Initialize FastAPI app
app = FastAPI(
    title="Morseverse",
    description="APIs for the Morseverse website",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc" ,  # ReDoc UI
    openapi_url="/openapi.json" ,  # OpenAPI schema
)

# Middleware (e.g., for CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routers
app.include_router(api_router, prefix="/api/v2")

# Main entry point
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
