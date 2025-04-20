import asyncio
import base64
import copy
import json
from collections import defaultdict
from typing import Annotated, Literal, List, Dict

from fastapi import APIRouter, HTTPException, Query, Path, Depends

from app.core.config import settings
from app.schemas.google_cloud import ImageBase64Response
from app.schemas.tryOn import TryOnRequest
from app.services.fashn_ai_service import generate_image_logic, FashnAIService
from app.services import gcs_async
import logging
import time

logger = logging.getLogger("character_logger")
FALLBACK_IMAGE_PATH = f"{settings.GCS_PUBLIC_BUCKET_URL}/character/2_w.jpeg"
router = APIRouter()


@router.get("/get-cloth/{category}", response_model=List[Dict])
async def get_cloth(category: Annotated[str, Literal["tops", "bottoms", "overwears", "fullbodys"]]):
    try:
        json_path = f"images/recommendation/{category}.json"
        json_content = await gcs_async.async_get_file_from_gcs(settings.GCS_BUCKET_NAME, json_path, as_text=True)
        clothing_data = json.loads(json_content).get("clothingData", [])

        return [
            {
                "id": f"{category}:{item['id']}:{i}",
                "type": item["category"].lower(),
                "name": item["name"],
                "image": f"{settings.GCS_PUBLIC_BUCKET_URL}{color['image']}",
                "price": float(item["price"].replace("$", ""))
            }
            for item in clothing_data
            for i, color in enumerate(item.get("colorOptions", []))
        ]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Data for category '{category}' not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON format.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/get-product/{product_id}", response_model=Dict)
async def get_product(product_id: str):
    try:
        category, product_number, color_index = product_id.split(":")
        product_number, color_index = int(product_number), int(color_index)

        json_path = f"images/recommendation/{category}.json"
        json_content = await gcs_async.async_get_file_from_gcs(settings.GCS_BUCKET_NAME, json_path, as_text=True)
        clothing_data = json.loads(json_content).get("clothingData", [])

        product = next((item for item in clothing_data if item["id"] == product_number), None)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")
        if color_index >= len(product.get("colorOptions", [])):
            raise HTTPException(status_code=400, detail="Invalid color index.")

        selected_color = copy.deepcopy(product["colorOptions"][color_index])
        selected_color["image"] = f"{settings.GCS_PUBLIC_BUCKET_URL}{selected_color['image']}"

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
                    "color": c["color"],
                    "image": f"{settings.GCS_PUBLIC_BUCKET_URL}{c['image']}",
                    "sizeOptions": c.get("sizeOptions", [])
                } for c in product.get("colorOptions", [])
            ]
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/get-image/{image_path:path}", response_model=ImageBase64Response)
async def get_image(image_path: str):
    try:
        image_content = await gcs_async.async_get_file_from_gcs(settings.GCS_BUCKET_NAME, image_path, as_text=False)
        image_base64 = base64.b64encode(image_content).decode("utf-8")
        return {"image_base64": image_base64}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


DEFAULT_SIZES = ["XS", "S", "M", "L", "XL"]

DEFAULT_SIZES = ["XS", "S", "M", "L", "XL"]

@router.get("/recommendation/{image_path:path}")
async def get_recommendation(image_path: str):
    try:
        category = image_path.split('/')[-2]
        json_path = f"images/recommendation/{category}.json"

        json_content = await gcs_async.async_get_file_from_gcs(
            settings.GCS_BUCKET_NAME,
            json_path,
            as_text=True
        )

        clothing_data = json.loads(json_content).get("clothingData", [])

        item = next(
            (
                item for item in clothing_data
                for color in item.get("colorOptions", [])
                if f"{settings.GCS_PUBLIC_BUCKET_URL}{color['image']}" == image_path
            ),
            None
        )

        if not item:
            raise HTTPException(status_code=404, detail="Item not found.")

        fashn_service = FashnAIService()
        recommendation = fashn_service.recommendation(item)

        if not recommendation or recommendation.get("status") != "success":
            raise HTTPException(status_code=500, detail="Error generating recommendations.")

        category_dict = defaultdict(list)
        product_map = {}
        all_color_map = defaultdict(lambda: defaultdict(dict))  # product_key -> color -> {image, sizes}

        for rec in recommendation["recommendations"]:
            rec["image"] = f"{settings.GCS_PUBLIC_BUCKET_URL}{rec['image']}"
            key = (rec["id"], rec["category"])

            # Save color info for later building allColors
            color = rec["color"]
            all_color_map[key][color].setdefault("image", rec["image"])
            all_color_map[key][color].setdefault("sizes", {})
            all_color_map[key][color]["sizes"][rec["size"]] = True

            # Init product if not already
            if key not in product_map:
                product_map[key] = {
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
                    "description": "",
                    "allColors": []  # filled later
                }
                category_dict[rec["category"]].append(product_map[key])

            # Add size to selectedColor
            if rec["color"] == product_map[key]["selectedColor"]["color"]:
                product_map[key]["selectedColor"]["sizeOptions"].append({
                    "size": rec["size"],
                    "available": True
                })

        # Now build allColors from recommendations
        for key, product in product_map.items():
            for color, data in all_color_map[key].items():
                color_entry = {
                    "color": color,
                    "image": data["image"],
                    "sizeOptions": []
                }
                for size in DEFAULT_SIZES:
                    color_entry["sizeOptions"].append({
                        "size": size,
                        "available": data["sizes"].get(size, False)
                    })
                product["allColors"].append(color_entry)

        return dict(category_dict)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/character_with_cloth/{main_character:path}", response_model=str)
async def get_character_image(
    main_character: str = Path(...),
    gender: str = Query(..., pattern="^(man|woman)$"),
    cloth_path: str = Query(...),
    try_on_request: TryOnRequest = Depends()
):
    start_time = time.time()
    logger.info(f"Request received | Character: {main_character}, Gender: {gender}, Cloth: {cloth_path}")

    supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp"]

    def strip_ext(filename: str) -> str:
        for ext in supported_extensions:
            if filename.lower().endswith(ext):
                return filename[:-len(ext)]
        return filename

    def normalize_path(path: str) -> str:
        return strip_ext(path.strip().lower().replace("/", "-").replace(" ", "_"))

    gender_suffix = "m" if gender == "man" else "w"
    character_stripped = strip_ext(main_character)
    cloth_stripped = strip_ext(cloth_path)

    if character_stripped == main_character or cloth_stripped == cloth_path:
        raise HTTPException(status_code=400, detail="Unsupported file extension.")

    normalized_character = normalize_path(main_character)
    if normalized_character.endswith(f"_{gender_suffix}"):
        normalized_character = normalized_character[:-len(f"_{gender_suffix}")]

    base_character = normalized_character.split("_")[0]
    previous_cloths = normalized_character.split("_")[1:]
    base_cloth = normalize_path(cloth_path)

    category_keywords = ["tops", "bottoms", "overwears", "fullbodys"]
    cloth_category = next((kw for kw in category_keywords if kw in cloth_path.lower()), "unknown")

    cloths_by_category = {cat: part for part in previous_cloths for cat in category_keywords if cat in part}
    cloths_by_category[cloth_category] = base_cloth
    sorted_cloths = [cloths_by_category[cat] for cat in category_keywords if cat in cloths_by_category]

    readable_filename = "_".join([base_character] + sorted_cloths + [gender_suffix]) + ".jpeg"
    gcs_file_path = f"character/{readable_filename}"

    if await gcs_async.async_check_file_exists_in_gcs(settings.GCS_BUCKET_NAME, gcs_file_path):
        return f"{settings.GCS_PUBLIC_BUCKET_URL}/{gcs_file_path}"

    try:
        main_img, cloth_img = await asyncio.gather(
            gcs_async.async_get_file_from_gcs(settings.GCS_BUCKET_NAME, f"character/{main_character}", as_text=False),
            gcs_async.async_get_file_from_gcs(settings.GCS_BUCKET_NAME, cloth_path, as_text=False)
        )
        main_b64 = base64.b64encode(main_img).decode("utf-8")
        cloth_b64 = base64.b64encode(cloth_img).decode("utf-8")

        generated = generate_image_logic(cloth_path, main_b64, cloth_b64)

        if generated and "result_image_base64" in generated:
            image_data = base64.b64decode(generated["result_image_base64"].split(",")[-1])
            await gcs_async.async_store_file_in_gcs(settings.GCS_BUCKET_NAME, gcs_file_path, image_data)
            return f"{settings.GCS_PUBLIC_BUCKET_URL}/{gcs_file_path}"

        return FALLBACK_IMAGE_PATH

    except Exception as e:
        logger.exception("Error generating or storing image.")
        return FALLBACK_IMAGE_PATH
