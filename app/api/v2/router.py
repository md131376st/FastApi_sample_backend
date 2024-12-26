import os
import importlib
import logging
from fastapi import APIRouter

# Initialize logging
logger = logging.getLogger("app")

# Create a centralized router
api_router = APIRouter()

# Tags mapping for API documentation
TAGS_MAPPING = {
    "subscription": "Subscriptions",
    "auth": "Authentication",
    "betasignup": "Demo",
    "google_cloud": "Google Cloud",
    "ai_agent": "AI Agent",
    "dashboard": "Dashboard",
    "google_drive": "Google Drive",
    "request": "Config",
    "tryOn": "fashion.ai",
}

# Define the package containing all endpoint modules
ENDPOINTS_PACKAGE = "app.api.v2.endpoints"


def register_routers(api_router: APIRouter, package: str, tags_mapping: dict):
    """
    Dynamically discover and register routers from the specified package.

    Args:
        api_router (APIRouter): The main API router to register endpoints.
        package (str): The name of the package containing the endpoint modules.
        tags_mapping (dict): A dictionary mapping module names to tags.

    Returns:
        None
    """
    # Get the path to the endpoints package
    package_path = os.path.join(os.path.dirname(__file__), "endpoints")

    if not os.path.isdir(package_path):
        logger.error(f"Endpoints directory not found: {package_path}")
        return

    # Iterate over all Python files in the endpoints directory
    for filename in os.listdir(package_path):
        if filename.endswith(".py") and filename != "__init__.py":
            # Build the module name
            module_name = f"{package}.{filename[:-3]}"  # Remove ".py"
            try:
                # Import the module dynamically
                module = importlib.import_module(module_name)

                # Ensure the module has a `router` attribute
                if hasattr(module, "router"):
                    # Get the tag for this module
                    tag = tags_mapping.get(filename[:-3], "Default")
                    api_router.include_router(module.router, tags=[tag])
                    logger.info(f"Registered router for {module_name} with tag: {tag}")
                else:
                    logger.warning(f"No 'router' found in module: {module_name}")
            except Exception as e:
                logger.error(f"Failed to register router for module {module_name}: {e}")


# Register all routers dynamically
register_routers(api_router, ENDPOINTS_PACKAGE, TAGS_MAPPING)
