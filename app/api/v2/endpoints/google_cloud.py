import base64
import copy
import hashlib
import json
from collections import defaultdict
from typing import Optional, Annotated, Literal, List, Dict

from fastapi import APIRouter, HTTPException, Query, Path, Depends

from app.core.config import settings
from app.schemas.google_cloud import Project, ImageBase64Response
from app.schemas.tryOn import TryOnRequest
from app.services.fashn_ai_service import generate_image_logic, FashnAIService
from app.services.gcs_service import get_file_from_gcs
import logging
from app.services import gcs_async

logger = logging.getLogger("character_logger")
FALLBACK_IMAGE_PATH = f"{settings.GCS_PUBLIC_BUCKET_URL}/character/2_w.jpeg"
router = APIRouter()


@router.get("/get-cloth/{category}", response_model=List[Dict])
async def get_cloth(category: Annotated[str, Literal["tops", "bottoms", "overwears", "fullbodys"]]):
    """
    Fetch structured product data from GCS where each image is a separate entry.

    Args:
        category (str): The category to fetch (e.g., "tops", "bottoms", "overwears").

    Returns:
        List[Dict]: A list where each image is an individual product entry.
    """
    try:
        json_path = f"images/recommendation/{category}.json"
        json_content = get_file_from_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=json_path, as_text=True)
        clothing_data = json.loads(json_content).get("clothingData", [])

        formatted_products = []

        for item in clothing_data:
            for color_index, color_option in enumerate(item.get("colorOptions", [])):
                formatted_products.append({
                    "id": f"{category}:{item['id']}:{color_index}",  # Unique ID format (category:id:colorIndex)
                    "type": item["category"].lower(),
                    "name": item["name"],
                    "image": f"{settings.GCS_PUBLIC_BUCKET_URL}{color_option['image']}",
                    "price": float(item["price"].replace("$", ""))
                })

        return formatted_products

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Data for category '{category}' not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error parsing JSON data from GCS.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/get-product/{product_id}", response_model=Dict)
async def get_product(product_id: str):
    """
    Fetch full product details from GCS JSON files based on the product ID.

    Args:
        product_id (str): The product identifier in the format "category:id:colorIndex".

    Returns:
        Dict: The full product details with a focus on the requested color.
    """
    try:
        # Extract category, product number, and color index
        try:
            category, product_number, color_index = product_id.split(":")
            product_number = int(product_number)  # Convert to integer for lookup
            color_index = int(color_index)  # Convert to integer for color lookup
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid product ID format.")

        # Path to the JSON file in GCS
        json_path = f"images/recommendation/{category}.json"

        # Fetch JSON data from GCS
        json_content = get_file_from_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=json_path, as_text=True)
        clothing_data = json.loads(json_content).get("clothingData", [])

        # Search for the product by ID
        product = next((item for item in clothing_data if item["id"] == product_number), None)

        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")

        # Ensure the requested color index exists
        if color_index >= len(product.get("colorOptions", [])):
            raise HTTPException(status_code=400, detail="Invalid color index for this product.")

        # Extract only the requested color details
        selected_color = copy.deepcopy(product["colorOptions"][color_index])
        selected_color["image"] = f"{settings.GCS_PUBLIC_BUCKET_URL}{selected_color['image']}"

        # Return the full product details but highlight the requested color
        return {
            "id": product["id"],
            "name": product["name"],
            "model": product["model"],
            "price": product["price"],
            "category": product["category"],
            "selectedColor": selected_color,
            "description": product.get("description", ""),
            "allColors": [
                {
                    "color": color_option["color"],
                    "image": f"{settings.GCS_PUBLIC_BUCKET_URL}{color_option['image']}",
                    "sizeOptions": color_option.get("sizeOptions", [])

                } for color_option in product.get("colorOptions", [])
            ]
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Data for category '{category}' not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error parsing JSON data from GCS.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/get-image/{image_path:path}", response_model=ImageBase64Response)
async def get_image(image_path: str):
    """
    Fetch an image from GCS based on the provided path and return it in Base64 format.
    The image path is relative to the GCS bucket.

    Example: images/project1/360image1.jpg
    """
    try:
        # Fetch the image file from GCS (as binary data)
        image_content = get_file_from_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=image_path, as_text=False)

        # Encode the binary content into base64
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # Return the base64-encoded image as a JSON response
        return {"image_base64": image_base64}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/recommendation/{image_path:path}")
async def get_recommendation(image_path: str):
    try:
        category = image_path.split('/')[-2]
        json_path = f"images/recommendation/{category}.json"

        # Use async GCS access if available
        json_content = await gcs_async.async_get_file_from_gcs(
            bucket_name=settings.GCS_BUCKET_NAME,
            file_path=json_path,
            as_text=True
        )

        # Parse JSON once
        clothing_data = json.loads(json_content).get("clothingData", [])

        # Fast lookup using a generator expression
        item = next(
            (
                clothing_item
                for clothing_item in clothing_data
                for color_option in clothing_item.get("colorOptions", [])
                if f"{settings.GCS_PUBLIC_BUCKET_URL}{color_option['image']}" == image_path
            ),
            None
        )

        if not item:
            raise HTTPException(status_code=404, detail="Item not found in the JSON file.")

        # Call recommendation logic
        fastion_service = FashnAIService()
        recommendation = fastion_service.recommendation(item)

        if not recommendation or recommendation.get("status") != "success":
            raise HTTPException(status_code=500, detail="Error generating recommendations")

        category_dict = defaultdict(list)
        product_map = {}

        for rec in recommendation["recommendations"]:
            rec["image"] = f"{settings.GCS_PUBLIC_BUCKET_URL}{rec['image']}"
            product_key = (rec["id"], rec["category"], rec["image"])

            if product_key not in product_map:
                product_map[product_key] = {
                    "id": rec["id"],
                    "name": rec["name"],
                    "model": rec["model"],
                    "price": str(rec["price"]),
                    "category": rec["category"],
                    "selectedColor": {
                        "color": rec["color"],
                        "image": rec["image"],
                        "sizeOptions": []
                    },
                    "description": f"{rec['name']} in {rec['color']}, model {rec['model']}",
                    "allColors": []
                }
                category_dict[rec["category"]].append(product_map[product_key])

            # Add sizes
            product_map[product_key]["selectedColor"]["sizeOptions"].append({"size": rec["size"]})

            # Add colors only if not already added
            if not any(c["color"] == rec["color"] for c in product_map[product_key]["allColors"]):
                product_map[product_key]["allColors"].append({
                    "color": rec["color"],
                    "image": rec["image"]
                })

        return dict(category_dict)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")



@router.get("/character_with_cloth/{main_character:path}", response_model=str)
async def get_character_image(
        main_character: str = Path(..., description="Character image path (e.g. '2_f.jpg')"),
        gender: str = Query(..., pattern="^(man|woman)$"),
        cloth_path: str = Query(..., description="Path to the clothing image"),
        try_on_request: TryOnRequest = Depends()
):
    logger.info(f"Incoming request | Character: {main_character}, Gender: {gender}, Cloth: {cloth_path}")

    supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp"]

    def strip_extension(filename: str) -> str:
        for ext in supported_extensions:
            if filename.lower().endswith(ext):
                return filename[: -len(ext)]
        return filename

    def normalize_gcs_path(path: str) -> str:
        return strip_extension(path.strip().lower().replace("/", "-").replace(" ", "_"))

    gender_identifier = "m" if gender == "man" else "w"

    # Normalize base character name
    normalized_character = normalize_gcs_path(main_character)
    if normalized_character.endswith(f"_{gender_identifier}"):
        normalized_character = normalized_character[: -len(f"_{gender_identifier}")]

    # Split into parts
    parts = normalized_character.split("_")
    base_character = parts[0]
    previous_cloths = parts[1:] if len(parts) > 1 else []

    # Normalize cloth
    base_cloth = normalize_gcs_path(cloth_path)

    # Extract cloth category (e.g., tops, bottoms, etc.)
    category_keywords = ["tops", "bottoms", "overwears", "fullbodys"]
    cloth_category = next((kw for kw in category_keywords if kw in cloth_path.lower()), "unknown")

    # Validate extensions
    if strip_extension(main_character) == main_character:
        raise HTTPException(status_code=400, detail="Unsupported file extension for main_character.")
    if strip_extension(cloth_path) == cloth_path:
        raise HTTPException(status_code=400, detail="Unsupported file extension for cloth_path.")

    cloth_exists = await gcs_async.async_check_file_exists_in_gcs(
        settings.GCS_BUCKET_NAME, file_path=cloth_path
    )
    if not cloth_exists:
        raise HTTPException(status_code=404, detail="Clothing image doesn't exist.")

    # Parse cloths by category
    cloths_by_category = { }
    for part in previous_cloths:
        for cat in category_keywords:
            if cat in part:
                cloths_by_category[cat] = part
                break

    # Override or add new cloth
    cloths_by_category[cloth_category] = base_cloth

    # Sort by category for consistency
    sorted_cloths = [cloths_by_category[cat] for cat in category_keywords if cat in cloths_by_category]

    readable_filename = "_".join([base_character] + sorted_cloths + [gender_identifier]) + ".jpeg"
    gcs_file_path = f"character/{readable_filename}"

    logger.info(f"[CACHING] Computed readable path: {gcs_file_path}")

    image_exists = await gcs_async.async_check_file_exists_in_gcs(
        settings.GCS_BUCKET_NAME, file_path=gcs_file_path
    )
    if image_exists:
        logger.info(f"[CACHING] Cached image found for: {gcs_file_path}")
        return f"{settings.GCS_PUBLIC_BUCKET_URL}/{gcs_file_path}"

    try:
        main_character_img = await gcs_async.async_get_file_from_gcs(
            settings.GCS_BUCKET_NAME, f"character/{main_character}", as_text=False
        )
        cloth_path_img = await gcs_async.async_get_file_from_gcs(
            settings.GCS_BUCKET_NAME, cloth_path, as_text=False
        )

        main_character_img_base64 = base64.b64encode(main_character_img).decode("utf-8")
        cloth_path_img_base64 = base64.b64encode(cloth_path_img).decode("utf-8")

        generated_image_content = generate_image_logic(
            cloth_path,
            main_character_img_base64,
            cloth_path_img_base64
        )

        if generated_image_content and "result_image_base64" in generated_image_content:
            base64_data = generated_image_content["result_image_base64"].split(",")[-1]
            image_data = base64.b64decode(base64_data)

            await gcs_async.async_store_file_in_gcs(
                settings.GCS_BUCKET_NAME, gcs_file_path, image_data
            )

            logger.info(f"[CACHING] Image generated and stored at: {gcs_file_path}")
            return f"{settings.GCS_PUBLIC_BUCKET_URL}/{gcs_file_path}"
        else:
            logger.warning("[GENERATION] Image generation failed. Using fallback.")
            return FALLBACK_IMAGE_PATH

    except Exception as e:
        logger.exception("[ERROR] Exception during image generation or GCS operations.")
        return FALLBACK_IMAGE_PATH


