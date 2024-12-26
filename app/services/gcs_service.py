import os
from typing import List, Dict, Optional

from google.cloud import storage
from app.core.config import settings  # Import the settings from your config


# Initialize the Google Cloud Storage client
def get_gcs_client():
    """
    Initialize and return a Google Cloud Storage client using the credentials
    set in the configuration file (Settings).
    """
    # Ensure the GOOGLE_APPLICATION_CREDENTIALS environment variable is set
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS not set in the environment.")

    # Create and return the storage client
    return storage.Client()


def get_file_from_gcs(bucket_name: str, file_path: str, as_text=True):
    """
    Fetches a file from Google Cloud Storage bucket.

    :param bucket_name: Name of the GCS bucket.
    :param file_path: Path of the file within the bucket.
    :param as_text: Whether to return the content as text (True) or binary (False).
    :return: Contents of the file as a string or binary depending on `as_text`.
    """
    try:
        # Check if the file exists using the helper function
        if not check_file_exists_in_gcs(bucket_name, file_path):
            raise FileNotFoundError(f"File {file_path} not found in bucket {bucket_name}")

        # Initialize the GCS client
        client = get_gcs_client()

        # Reference the GCS bucket
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        # Download the file content as text or binary
        if as_text:
            return blob.download_as_text()
        else:
            return blob.download_as_bytes()  # For binary files like images

    except Exception as e:
        raise RuntimeError(f"An error occurred while fetching the file from GCS: {str(e)}")

def list_images_in_bucket(bucket_name: str, prefix: str = "", selected_categories: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """
    List image URLs in a specified Google Cloud Storage bucket and optional prefix (folder).

    Args:
        bucket_name (str): The name of the Google Cloud Storage bucket.
        prefix (str): Optional folder path within the bucket to filter images.
        selected_categories (List[str]): List of categories to filter, defaults to all categories if None.

    Returns:
        Dict[str, List[str]]: A dictionary containing lists of image URLs categorized by selected or default categories.
    """
    storage_client = get_gcs_client()
    all_categories = {"tops": [], "bottoms": [], "overwears": []}
    category_list = {k: [] for k in (selected_categories or all_categories.keys())}

    try:
        # Access the specified bucket
        bucket = storage_client.bucket(bucket_name)

        # List all blobs in the bucket with the given prefix
        for category in category_list.keys():
            blobs = bucket.list_blobs(prefix=f"{prefix}/{category}")

            # Filter and add only image files to the list
            category_list[category] = [
                blob.name for blob in blobs
                if blob.name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp"))
            ]

    except Exception as e:
        print(f"Error accessing the bucket: {str(e)}")
        return category_list

    return category_list

def check_file_exists_in_gcs(bucket_name: str, file_path: Optional[str] = None, prefix: Optional[str] = None) -> Optional[str]:
    """
    Checks if a file exists in a Google Cloud Storage bucket. Can check for a specific file or files matching a prefix.

    :param bucket_name: Name of the GCS bucket.
    :param file_path: Specific file path to check (optional).
    :param prefix: Prefix to search for matching files (optional).
    :return: The file name if it exists, or None if no match is found.
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)

        if file_path:
            # Check for a specific file
            blob = bucket.blob(file_path)
            return file_path if blob.exists() else None
        elif prefix:
            # Check for files matching the prefix
            blobs = list(bucket.list_blobs(prefix=prefix))
            return blobs[0].name if blobs else None
        else:
            raise ValueError("Either 'file_path' or 'prefix' must be provided.")

    except Exception as e:
        raise RuntimeError(f"An error occurred while checking the file in GCS: {str(e)}")

def store_file_in_gcs(bucket_name: str, file_path: str, content: bytes):
    """
    Uploads a file to the specified GCS bucket.
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.upload_from_string(content)
        print(f"File {file_path} successfully uploaded to bucket {bucket_name}.")
    except Exception as e:
        raise RuntimeError(f"Failed to upload file to GCS: {str(e)}")