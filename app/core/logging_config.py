from .config import settings
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(pathname)s:%(lineno)d]",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "detailed",
            "filename": "logs/app.log",
        },
    },
    "loggers": {
        "app": {
            "handlers": ["console", "file"],
            "level": settings.LOG_LEVEL,  # Use LOG_LEVEL from settings
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": settings.LOG_LEVEL,  # Use LOG_LEVEL from settings
    },
}

# Configure logging
dictConfig(LOGGING_CONFIG)
