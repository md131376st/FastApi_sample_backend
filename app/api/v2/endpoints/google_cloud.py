import base64
import copy
import hashlib
import json
from typing import Optional, Annotated, Literal, List, Dict

from fastapi import APIRouter, HTTPException, Query, Path, Depends

from app.core.config import settings
from app.schemas.google_cloud import Project, ImageBase64Response
from app.schemas.tryOn import TryOnRequest
from app.services.fashn_ai_service import generate_image_logic, FashnAIService
from app.services.gcs_service import get_file_from_gcs, list_images_in_bucket, check_file_exists_in_gcs, \
    store_file_in_gcs

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
    print("hi")
    try:
        category = image_path.split('/')[-2]
        json_path = f"images/recommendation/{category}.json"
        json_content = get_file_from_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=json_path, as_text=True)
        clothing_data = json.loads(json_content).get("clothingData", [])
        item = {}
        for clothing_item in clothing_data:
            for color_option in clothing_item.get("colorOptions", []):
                if f"{settings.GCS_PUBLIC_BUCKET_URL}{color_option["image"]}" == image_path:
                    item = clothing_item
                    break
            if item:
                break
        print(item)
        if not item:
            return HTTPException(status_code=404, detail="Item not found in the JSON file.")

        fastion_service = FashnAIService()
        recommendation = fastion_service.recommendation(item)
        if recommendation is None:
            return HTTPException(status_code=500, detail="Error generating recommendations ")
        if recommendation["status"] == "success":
            products = []
            product_map = {}

            for item in recommendation["recommendations"]:
                product_key = (item["id"], item["category"],item["image"])
                item["image"] = f"{settings.GCS_PUBLIC_BUCKET_URL}{item["image"]}"
                if product_key not in product_map:
                    product = {
                        "id": item["id"],
                        "name": item["name"],
                        "model": item["model"],
                        "price": str(item["price"]),
                        "category": item["category"],
                        "selectedColor": {
                            "color": item["color"],
                            "image": item["image"],
                            "sizeOptions": []
                        },
                        "description": f"{item['name']} in {item['color']}, model {item['model']}",
                        "allColors": []
                    }
                    product_map[product_key] = product
                    products.append(product)

                # Add sizes
                product_map[product_key]["selectedColor"]["sizeOptions"].append({"size": item["size"]})

                # Ensure unique colors
                if not any(c["color"] == item["color"] for c in product_map[product_key]["allColors"]):
                    product_map[product_key]["allColors"].append({"color": item["color"], "image": item["image"]})

            return products
        else:
            return HTTPException(status_code=500, detail="Error generating recommendations ")
    except:
        return HTTPException(status_code=500, detail=f"Error accessing the bucket")


@router.get("/character_with_cloth/{main_character:path}", response_model=str)
async def get_character_image(
        main_character: str = Path(..., description="BucketPath"),
        gender: str = Query(..., regex="^(man|woman)$"),
        cloth_path: str = Query(..., description="Path to the clothing resource"),
        # `None` allows the parameter to be optional
        try_on_request: TryOnRequest = Depends()
):
    """
       generate the character with cloth
       included in main_character path: images/character/
       main_character defult = 2_f.jpg
       no need for bucket
       clothpath = images/recommendation/bottoms/00f9272f652fde49cae740deab4efec4.jpg
       """
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
    exstantion = ""
    for ext in supported_extensions:
        if cloth_path.endswith(ext):
            base_cloth = main_character[: -len(ext)]  # Strip the extension
            exstantion = ext
            break
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension in main_character. Supported extensions are: {', '.join(supported_extensions)}"
        )

    # Create a unique hash for the file name based on main_character and cloth_path
    hash_input = f"{base_character}_{base_cloth}" if cloth_path else base_character
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()

    # Construct the file path for GCS

    gcs_file_path = f"character/{hash_value}_{gender_identifier}.jpeg"

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
            main_character=f"character/{main_character}",
            cloth_path=cloth_path,
            file_path=gcs_file_path
        )
        if generated_image_path:
            return generated_image_path
        else:
            raise HTTPException(status_code=500, detail="Internal server error")

    if cloth_path and not check_file_exists_in_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=cloth_path):
        raise HTTPException(status_code=404, detail="Image doesn't exist")
    print("hi")
    return f"{settings.GCS_PUBLIC_BUCKET_URL}/{gcs_file_path}"


def generate_image_and_store(
        bucket_name: str,
        main_character: str,
        cloth_path: str,
        file_path: str
) -> str:
    # Simulate image generation logic and store it in the bucket
    # getbase64Images
    # main_character => form the charector path of the bucket
    # cloth_path => from

    main_character_img = get_file_from_gcs(bucket_name=bucket_name, file_path=main_character, as_text=False)

    # Encode the binary content into base64
    main_character_img_base64 = base64.b64encode(main_character_img).decode('utf-8')
    cloth_path_img = get_file_from_gcs(bucket_name=bucket_name, file_path=cloth_path, as_text=False)

    # Encode the binary content into base64
    cloth_path_img_base64 = base64.b64encode(cloth_path_img).decode('utf-8')
    generated_image_content = generate_image_logic(
        cloth_path,
        main_character_img_base64,
        cloth_path_img_base64
    )
    if generated_image_content:
        base64_data = generated_image_content["result_image_base64"].split(",")[1]

        image_data = base64.b64decode(base64_data)

        if generated_image_content:
            store_file_in_gcs(
                bucket_name,
                file_path,
                image_data
            )
        return f"{settings.GCS_PUBLIC_BUCKET_URL}/{file_path}"
    return ""
