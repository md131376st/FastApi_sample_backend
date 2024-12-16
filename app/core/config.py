import os

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # MongoDB configuration
    PRODUCTION: bool = (os.getenv('Production', 'False') == 'True')
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "fastapi_db_v2")
    MONGODB_DB_NAME_SPETIAL_AI: str = os.getenv("MONGODB_DB_NAME_SPETIAL_AI", "fastapi_db_v2")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    DOMAIN: str = os.getenv("DOMAIN", "http://127.0.0.1:8000")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # Token validity

    # Email settings
    SMTP_USER: str = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@example.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Your app")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # Database settings (if needed)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb://localhost:27017")

    # # Other application settings (e.g., API keys, secret keys, etc.)
    # SECRET_KEY: str = "your-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # Token expiry time in minutes

    # Google Cloud settings
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "your-gcs-bucket")
    GCS_FILE_PATH: str = os.getenv("GCS_FILE_PATH", "path/to/coordinates.json")

    GCS_RECOMMENDATION_PATH: str = os.getenv("GCS_RECOMMENDATION_PATH", "path/to/recommendations")
    # AI_Agent
    AI_SITE: str = os.getenv("AI_SITE", "default")

    class Config:
        env_file = ".env"  # Load variables from .env file if it exists


# Create an instance of the Settings class
settings = Settings()
