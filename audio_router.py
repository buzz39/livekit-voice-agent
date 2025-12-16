
import os
import logging
import asyncio
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from neon_db import get_db

logger = logging.getLogger("audio-router")

audio_router = APIRouter(prefix="/dashboard")

# Executor for blocking S3 calls
executor = ThreadPoolExecutor(max_workers=5)

def get_s3_client():
    """Create S3 client from environment variables."""
    access_key = os.getenv("S3_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    endpoint_url = os.getenv("S3_ENDPOINT")
    region_name = os.getenv("S3_REGION") or os.getenv("AWS_REGION")

    if not (access_key and secret_key):
        return None

    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )

def extract_bucket_and_key(recording_url: str) -> tuple[str, str]:
    """
    Extracts bucket and key from a recording URL.
    Returns (bucket, key) or (None, None).
    """
    if not recording_url:
        return None, None

    # Get configured bucket as fallback/context
    env_bucket = os.getenv("S3_BUCKET") or os.getenv("S3_BUCKET_NAME")

    parsed = urlparse(recording_url)
    path = parsed.path
    key = None

    # Strategy 1: standard path style (endpoint/bucket/key)
    if env_bucket:
        path_style_prefix = f"/{env_bucket}/"
        if path_style_prefix in path:
            key = path.split(path_style_prefix, 1)[1]
            return env_bucket, key

    # Strategy 2: virtual hosted style (bucket.s3.../key)
    if parsed.netloc and env_bucket and parsed.netloc.startswith(env_bucket):
         key = path.lstrip("/")
         return env_bucket, key

    # Strategy 3: Just use the filename if all else fails
    if path.endswith(".mp4"):
        if env_bucket:
             if not key:
                 key = path.lstrip("/")
             return env_bucket, key

    return None, None

def fetch_s3_stream(bucket, key):
    """Blocking S3 call to be run in executor."""
    s3 = get_s3_client()
    if not s3:
        raise ValueError("S3 client not configured")
    try:
        return s3.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        logger.warning(f"S3 Error for {bucket}/{key}: {e}")
        return None

@audio_router.get("/audio/{call_id}")
async def stream_audio(call_id: int):
    """
    Streams the audio recording for a given call ID.
    Proxies the content from S3 to the client.
    """
    db = await get_db()
    try:
        call = await db.get_call(call_id)
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        recording_url = call.get("recording_url")
        if not recording_url:
            raise HTTPException(status_code=404, detail="No recording found for this call")

        bucket, key = extract_bucket_and_key(recording_url)

        if not bucket or not key:
             logger.error(f"Could not extract bucket/key from {recording_url}")
             raise HTTPException(status_code=500, detail="Invalid recording configuration")

        # Run blocking S3 call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(executor, fetch_s3_stream, bucket, key)

        if not response:
             raise HTTPException(status_code=404, detail="Audio file not found or inaccessible")

        return StreamingResponse(
            response['Body'],
            media_type="audio/mp4",
            headers={
                "Content-Disposition": f"inline; filename={key.split('/')[-1]}",
            }
        )

    except ValueError:
        raise HTTPException(status_code=500, detail="Server configuration error")
    except Exception as e:
        logger.error(f"Unexpected error streaming audio: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.close()
