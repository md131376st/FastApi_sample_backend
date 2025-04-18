import os
from typing import List, Optional
import logging
from google.cloud import storage
from app.core.config import settings
from app.core.enums import FashnCategory
from app.schemas.fashn_category_model import FashnCategoryModel

logger = logging.getLogger(__name__)

# Create a singleton GCS client to reuse
_gcs_client: Optional[storage.Client] = None

def get_gcs_client() -> storage.Client:
    """
    Initialize and return a Google Cloud Storage client using the credentials
    set in the configuration file.
    """
    global _gcs_client
    if _gcs_client is None:
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS not set in the environment.")
        _gcs_client = storage.Client()
    return _gcs_client


def get_file_from_gcs(bucket_name: str, file_path: str, as_text: bool = True):
    """
    Fetch a file from GCS and return its contents as text or bytes.
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        if not blob.exists():
            raise FileNotFoundError(f"File '{file_path}' not found in bucket '{bucket_name}'.")

        return blob.download_as_text() if as_text else blob.download_as_bytes()

    except Exception as e:
        raise RuntimeError(f"Failed to fetch file from GCS: {e}")


def list_images_in_bucket(
    bucket_name: str,
    prefix: str = "",
    selected_categories: Optional[List[FashnCategory]] = None
) -> FashnCategoryModel:
    """
    Lists image files in GCS bucket under specific category prefixes.
    """
    client = get_gcs_client()
    category_model = FashnCategoryModel()
    categories_to_list = selected_categories or list(FashnCategory)

    try:
        bucket = client.bucket(bucket_name)

        for category in categories_to_list:
            full_prefix = f"{prefix}/{category.value}"
            blobs = bucket.list_blobs(prefix=full_prefix)
            category_model.categories[category] = [
                blob.name for blob in blobs
                if blob.name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp"))
            ]

    except Exception as e:
        logger.error(f"Error listing images in bucket: {e}")

    return category_model


def check_file_exists_in_gcs(bucket_name: str, file_path: Optional[str] = None, prefix: Optional[str] = None) -> bool:
    """
    Checks if a file or files with a prefix exist in GCS.

    :return: True if exists, False otherwise.
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)

        if file_path:
            return bucket.get_blob(file_path) is not None

        if prefix:
            blobs = list(bucket.list_blobs(prefix=prefix))
            return len(blobs) > 0

        raise ValueError("Either 'file_path' or 'prefix' must be provided.")

    except Exception as e:
        raise RuntimeError(f"Error checking file existence in GCS: {e}")


def store_file_in_gcs(bucket_name: str, file_path: str, content: bytes, content_type: str = "image/jpeg"):
    """
    Uploads a file to a GCS bucket.
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.upload_from_string(content, content_type=content_type)
        logger.info(f"File uploaded to GCS: {file_path}")

    except Exception as e:
        raise RuntimeError(f"Failed to upload file to GCS: {e}")
