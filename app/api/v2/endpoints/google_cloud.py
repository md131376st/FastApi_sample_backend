import base64
import json
import os
import random

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.google_cloud import Project, ImageBase64Response, RecommendationList
from app.services.gcs_service import get_file_from_gcs, list_images_in_bucket

router = APIRouter()


@router.get("/get-coordinates/{project_name}", response_model=Project)
async def get_coordinates(project_name: str):
    """
    Fetch the coordinates JSON file from GCS and return the content
    specific to the given project_name, including URLs for images.
    """
    try:
        # Fetch the content of the JSON file from GCS
        content = get_file_from_gcs(bucket_name=settings.GCS_BUCKET_NAME, file_path=settings.GCS_FILE_PATH,
                                    as_text=True)

        # Parse the JSON content
        data = json.loads(content)

        # Search for the project by name
        for project in data.get("projects", []):
            if project["projectName"].lower() == project_name.lower():
                # Update the image paths to be URLs (either public or signed URLs)
                for image in project["images"]:
                    # If you want to use signed URLs, uncomment the next line
                    # image["image"] = get_signed_url(settings.GCS_BUCKET_NAME, image["image"])

                    # If your files are public, use the public URL
                    image["image"] = f"{image['image']}"

                    # Update coordinates image URLs
                    for coord in image["coordinates"]:
                        coord["image"] = coord['image']

                return project

        # If no matching project was found, return a 404 error
        raise FileNotFoundError()

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found.")
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
        recommended_images=dict()
        for category, items in recommendation.items():
            if len(items) < 2:
                raise HTTPException(status_code=400, detail="Not enough images in the bucket to provide recommendations")

            # Randomly select 5 images
        # recommended_images = random.sample(list_recommendation, 5)
            recommended_images[category] = items[:2]

        return RecommendationList(image_paths =recommended_images)
    except :
        raise HTTPException(status_code=500, detail=f"Error accessing the bucket")


