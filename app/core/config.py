import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()


class Settings(BaseSettings):
    # MongoDB configuration
    PRODUCTION: bool = Field(default=(os.getenv('Production', 'False') == 'True'))
    MONGODB_URL: str = Field(default=os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
    MONGODB_DB_NAME: str = Field(default=os.getenv("MONGODB_DB_NAME", "fastapi_db_v2"))
    MONGODB_DB_NAME_SPETIAL_AI: str = Field(default=os.getenv("MONGODB_DB_NAME_SPETIAL_AI", "fastapi_db_v2"))

    # Security
    SECRET_KEY: str = Field(default=os.getenv("SECRET_KEY", "your-secret-key"))
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=120)

    # Domain
    DOMAIN: str = Field(default=os.getenv("DOMAIN", "http://127.0.0.1:8000"))

    # Email settings
    SMTP_USER: str = Field(default=os.getenv("SMTP_USER"))
    SMTP_PASSWORD: str = Field(default=os.getenv("SMTP_PASSWORD"))
    SMTP_HOST: str = Field(default=os.getenv("SMTP_HOST", "smtp.gmail.com"))
    SMTP_PORT: int = Field(default=int(os.getenv("SMTP_PORT", 587)))
    EMAIL_FROM: str = Field(default=os.getenv("EMAIL_FROM", "noreply@example.com"))
    EMAIL_FROM_NAME: str = Field(default=os.getenv("EMAIL_FROM_NAME", "Your app"))

    # Database settings
    DATABASE_URL: str = Field(default=os.getenv("DATABASE_URL", "mongodb://localhost:27017"))

    # Google Cloud settings
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    GCS_BUCKET_NAME: str = Field(default=os.getenv("GCS_BUCKET_NAME", "your-gcs-bucket"))
    GCS_FILE_PATH: str = Field(default=os.getenv("GCS_FILE_PATH", "path/to/coordinates.json"))
    GCS_RECOMMENDATION_PATH: str = Field(default=os.getenv("GCS_RECOMMENDATION_PATH", "path/to/recommendations"))
    GCS_MAIN_IMAGE_DIRECTORY:str = Field(default=os.getenv("GCS_MAIN_IMAGE_DIRECTORY", "path/to/image") )

    # AI_Agent
    AI_SITE: str = Field(default=os.getenv("AI_SITE", "default"))

    # Logging
    LOG_LEVEL: str = Field(default=os.getenv("LOG_LEVEL", "DEBUG"))



    # Configure Google credentials as an environment variable
    class Config:
        env_file = ".env"


# Create an instance of the Settings class
settings = Settings()

# Set Google credentials dynamically
if settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
