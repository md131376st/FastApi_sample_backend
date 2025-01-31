import base64
import copy
import hashlib
import json
from typing import Optional, Annotated, Literal, List, Dict

from fastapi import APIRouter, HTTPException, Query, Path, Depends

from app.core.config import settings
from app.schemas.google_cloud import Project, ImageBase64Response, RecommendationList
from app.schemas.tryOn import TryOnRequest
from app.services.gcs_service import get_file_from_gcs, list_images_in_bucket, check_file_exists_in_gcs, \
    store_file_in_gcs
from app.services.tryOn_ai_service import generate_image_logic

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
                    "image": f"{settings.GCS_PUBLIC_BUCKET_URL}{color_option['image']}"
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


@router.get("/recommendation/{image_path:path}", response_model=RecommendationList)
async def get_recommendation(image_path: str):
    try:
        recommendation = list_images_in_bucket(bucket_name=settings.GCS_BUCKET_NAME,
                                               prefix=settings.GCS_RECOMMENDATION_PATH)
        recommended_images = dict()
        for category, items in recommendation.items():
            if len(items) < 2:
                raise HTTPException(status_code=400,
                                    detail="Not enough images in the bucket to provide recommendations")

            # Randomly select 5 images
            # recommended_images = random.sample(list_recommendation, 5)
            recommended_images[category] = items[:2]

        return RecommendationList(image_paths=recommended_images)
    except:
        raise HTTPException(status_code=500, detail=f"Error accessing the bucket")


@router.get("/character_with_cloth/{main_character:path}", response_model=str)
async def get_character_image(
        main_character: str = Path(..., description="BucketPath"),
        gender: str = Query(..., regex="^(man|woman)$"),
        cloth_path: str =Query(..., description="Path to the clothing resource"),  # `None` allows the parameter to be optional
        try_on_request: TryOnRequest = Depends()
):
    # Determine the correct gender identifier
    gender_identifier = "m" if gender == "man" else "w"

    # Supported image extensions
    supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp"]

    # Check if the main_character has a valid image extension
    for ext in supported_extensions:
        if main_character.endswith(ext):
            base_character = main_character[: -len(ext)]  # Strip the extension
            break
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension in main_character. Supported extensions are: {', '.join(supported_extensions)}"
        )

    # Create a unique hash for the file name based on main_character and cloth_path
    hash_input = f"{main_character}_{cloth_path}" if cloth_path else main_character
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()

    # Construct the file path for GCS
    gcs_file_path = f"{settings.GCS_MAIN_IMAGE_DIRECTORY}/character/{hash_value}_{gender_identifier}"

    # Check if an image exists with the specified prefix
    def find_image_with_prefix(prefix: str) -> Optional[str]:
        # Replace with actual implementation for checking GCS or file storage
        matched_file = check_file_exists_in_gcs(bucket_name=settings.GCS_BUCKET_NAME, prefix=prefix)
        return matched_file

    image_path = find_image_with_prefix(gcs_file_path)

    if not image_path:
        # Call a function to generate the image if no image with the prefix exists
        generated_image_path = generate_image_and_store(
            bucket_name=settings.GCS_BUCKET_NAME,
            file_path=gcs_file_path,
            try_on_request=try_on_request
        )
        return generated_image_path

    if cloth_path and not check_file_exists_in_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=cloth_path):
        raise HTTPException(status_code=404, detail="Image doesn't exist")

    return gcs_file_path


def generate_image_and_store(bucket_name: str, file_path: str, try_on_request: TryOnRequest) -> str:
    # Simulate image generation logic and store it in the bucket
    generated_image_content = generate_image_logic(try_on_request)  # Implement your logic for image generation
    store_file_in_gcs(bucket_name, file_path, generated_image_content)
    return f"{bucket_name}/{file_path}"
