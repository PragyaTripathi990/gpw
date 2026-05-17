"""
Google Cloud Storage service for storing uploaded documents.
"""
import uuid
from datetime import datetime
from google.cloud import storage
from backend.config import GCS_BUCKET_NAME


def get_storage_client():
    """Get GCS client."""
    return storage.Client()


def upload_to_gcs(file_content: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    """Upload a file to Google Cloud Storage and return the GCS URI."""
    try:
        client = get_storage_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        
        # Create unique filename
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"uploads/{timestamp}_{unique_id}_{filename}"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_string(file_content, content_type=content_type)
        
        return f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    except Exception as e:
        print(f"GCS upload failed: {e}")
        return ""


def create_bucket_if_not_exists():
    """Create the GCS bucket if it doesn't exist."""
    try:
        client = get_storage_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        if not bucket.exists():
            bucket = client.create_bucket(GCS_BUCKET_NAME, location="us-central1")
            print(f"Created bucket: {GCS_BUCKET_NAME}")
        return True
    except Exception as e:
        print(f"Bucket creation failed: {e}")
        return False
