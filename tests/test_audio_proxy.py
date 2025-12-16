
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from audio_router import extract_bucket_and_key, audio_router

# Test the extraction logic
def test_extract_bucket_and_key():
    # Strategy 1: Path style with configured bucket
    with patch("os.getenv", side_effect=lambda k: "my-bucket" if k == "S3_BUCKET" else None):
        bucket, key = extract_bucket_and_key("https://endpoint.com/my-bucket/folder/file.mp4")
        assert bucket == "my-bucket"
        assert key == "folder/file.mp4"

    # Strategy 2: Virtual hosted style
    with patch("os.getenv", side_effect=lambda k: "my-bucket" if k == "S3_BUCKET" else None):
        bucket, key = extract_bucket_and_key("https://my-bucket.s3.amazonaws.com/folder/file.mp4")
        assert bucket == "my-bucket"
        assert key == "folder/file.mp4"

    # Strategy 3: Filename fallback
    with patch("os.getenv", side_effect=lambda k: "my-bucket" if k == "S3_BUCKET" else None):
        bucket, key = extract_bucket_and_key("https://random.com/path/file.mp4")
        assert bucket == "my-bucket"
        assert key == "path/file.mp4"

    # No configured bucket -> logic might fail for strats 1 & 2 but return nothing if strict
    with patch("os.getenv", return_value=None):
        bucket, key = extract_bucket_and_key("https://endpoint.com/bucket/key.mp4")
        assert bucket is None
        assert key is None
