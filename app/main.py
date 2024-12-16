from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.v2.router import api_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, close_db
from app.google_drive import close_google_drive, init_google_drive

# Initialize FastAPI app

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
        await init_db()
        await init_google_drive()
        yield
    except Exception as e:
        print(f"Error during startup: {e}")
    finally:
        # Clean up resources during shutdown
        await close_google_drive()
        await close_db()


app = FastAPI(
    title="morseverse",
    description="website apis ",
    version="2.0.0",
    lifespan=lifespan

)
# Middleware (e.g., for CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Update this with specific domains in production
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
