import os
from typing import List, Dict

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
        # Initialize the GCS client
        client = get_gcs_client()

        # Reference the GCS bucket
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        # Check if the file (blob) exists
        if not blob.exists():
            raise FileNotFoundError(f"File {file_path} not found in bucket {bucket_name}")

        # Download the file content as text or binary
        if as_text:
            return blob.download_as_text()
        else:
            return blob.download_as_bytes()  # For binary files like images

    except Exception as e:
        raise RuntimeError(f"An error occurred while fetching the file from GCS: {str(e)}")


def list_images_in_bucket(bucket_name: str, prefix: str = "")-> Dict[str, List[str]]:
    """
    List image URLs in a specified Google Cloud Storage bucket and optional prefix (folder).

    Args:
        bucket_name (str): The name of the Google Cloud Storage bucket.
        prefix (str): Optional folder path within the bucket to filter images.

    Returns:
        List[str]: A list of URLs for images in the bucket.
    """
    storage_client = get_gcs_client()
    category_list = {"tops": [], "bottoms": []}

    try:
        # Access the specified bucket
        bucket = storage_client.bucket(bucket_name)

        # List all blobs in the bucket with the given prefix

        for category  in category_list.keys():
            blobs = bucket.list_blobs(prefix=f"{prefix}/{category}")

            # Filter and add only image files to the list
            category_list[category] = [
                blob.name for blob in blobs
                if blob.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
            ]

    except Exception as e:
        print(f"Error accessing the bucket: {str(e)}")
        return category_list

    return category_list
