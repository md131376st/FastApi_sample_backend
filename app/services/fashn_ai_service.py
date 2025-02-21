import base64
import logging

from app.core.config import Settings
from app.core.external_service import ExternalService
from app.core.enums import FashnCategory
from app.schemas.fashn_category_model import FashnCategoryModel
from app.schemas.tryOn import TryOnRequest


class FashnAIService(ExternalService):
    """
    Service class for interacting with the FASHN AI Prediction API.
    """

    def __init__(self):
        base_url = f"{Settings.AI_SITE}/fashn"
        super().__init__(base_url)  # No API key required
        self.category_model = FashnCategoryModel()  # Base model instance

    @staticmethod
    def encode_image(image_path: str) -> str:
        """
        Converts an image file to a base64-encoded string.
        """
        try:
            with open(image_path, "rb") as img_file:
                return f"data:image/jpeg;base64,{base64.b64encode(img_file.read()).decode('utf-8')}"
        except FileNotFoundError:
            logging.error(f"File not found: {image_path}")
            return None

    def predict(self, model_image_path: str, garment_image_path: str, category: FashnCategory):
        """
        Sends a request to the FASHN AI Prediction API.

        :param model_image_path: Path to the model image (base64 encoded).
        :param garment_image_path: Path to the garment image (base64 encoded).
        :param category: Category of the garment (must be a FashnCategory enum value).
        :return: Base64-encoded predicted image or error message.
        """

        if not isinstance(category, FashnCategory):
            logging.error(f"Invalid category '{category}'. Must be one of {FashnCategory.list()}.")
            return None


        endpoint = "predict"
        data = {
            "model_image_base64": model_image_path,
            "garment_image_base64": garment_image_path,
            "category": category.value  # Convert Enum to string
        }

        response = self.post(endpoint, data=data)

        if response and response.get("status") == "completed":
            return {
                "result_image_base64": response["result_image_base64"],
                "execution_time": response["execution_time"]
            }
        else:
            logging.error(f"Prediction failed: {response.get('detail', 'Unknown error')}")
            return None

    def add_garment(self, category: FashnCategory, garment_name: str):
        """
        Adds a garment to the category model.
        """
        try:
            self.category_model.add_garment(category, garment_name)
            logging.info(f"Added '{garment_name}' to category '{category.value}'")
        except ValueError as e:
            logging.error(str(e))


def generate_image_logic(main_character, cloth_path) -> str:
    ai_service = FashnAIService()

    # Valid prediction request
    result = ai_service.predict(main_character, cloth_path, category=FashnCategory.TOPS)

    if result:
        print("Predicted Image (Base64):", result["result_image_base64"])
        print("Execution Time:", result["execution_time"])
    else:
        print("Prediction failed.")
