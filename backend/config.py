"""LexGuard Configuration"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

# Google Cloud Settings
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "lexguard-uploads")

# Model Settings
GEMINI_PRO_MODEL = "gemini-2.5-pro"
GEMINI_FLASH_MODEL = "gemini-2.5-flash"

# Risk Thresholds
CRITICAL_RISK_THRESHOLD = 8
WARNING_RISK_THRESHOLD = 5

# Document AI Processor (set after creating processor in GCP)
DOCUMENT_AI_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
