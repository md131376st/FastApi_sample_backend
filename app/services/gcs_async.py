from starlette.concurrency import run_in_threadpool

from app.services.gcs_service import get_file_from_gcs, check_file_exists_in_gcs, store_file_in_gcs


async def async_get_file_from_gcs(bucket_name: str, file_path: str, as_text: bool = True):
    return await run_in_threadpool(get_file_from_gcs, bucket_name, file_path, as_text)


async def async_check_file_exists_in_gcs(bucket_name: str, file_path: str = None, prefix: str = None):
    return await run_in_threadpool(check_file_exists_in_gcs, bucket_name, file_path, prefix)


async def async_store_file_in_gcs(bucket_name: str, file_path: str, content: bytes, type: str = "image/jpeg"):
    await run_in_threadpool(store_file_in_gcs, bucket_name, file_path, content, type)
