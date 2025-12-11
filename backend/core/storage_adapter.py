"""
Storage Adapter for Vercel Serverless Environment
Handles file storage with fallback to /tmp for serverless environments
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Detect if running on Vercel
IS_VERCEL = os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") is not None

# For Vercel, use /tmp for temporary storage
# Note: /tmp is ephemeral and will be cleared between function invocations
# For production, you should use Vercel Blob Storage or an external database
if IS_VERCEL:
    BASE_STORAGE_DIR = Path("/tmp/nexus_data")
else:
    # Local development - use project data directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ROOT_DIR = os.path.dirname(BASE_DIR)
    BASE_STORAGE_DIR = Path(ROOT_DIR) / "data"

# Ensure storage directory exists
try:
    BASE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Storage directory initialized: {BASE_STORAGE_DIR}")
except Exception as e:
    logger.error(f"Failed to create storage directory: {e}", exc_info=True)
    # Always fallback to /tmp if creation fails (works on both local and Vercel)
    BASE_STORAGE_DIR = Path("/tmp/nexus_data")
    try:
        BASE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Using fallback storage: {BASE_STORAGE_DIR}")
    except Exception as e2:
        logger.error(f"Failed to create fallback storage: {e2}", exc_info=True)
        raise

DATA_DIR = BASE_STORAGE_DIR
CANVASES_DIR = DATA_DIR / "canvases"
CANVAS_INDEX_FILE = DATA_DIR / "canvases.json"
SETTINGS_FILE = DATA_DIR / "nexus_settings.json"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"

def ensure_dirs():
    """Ensure all required directories exist"""
    CANVASES_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

def get_storage_info() -> Dict[str, Any]:
    """Get information about current storage configuration"""
    return {
        "is_vercel": IS_VERCEL,
        "storage_dir": str(DATA_DIR),
        "is_ephemeral": IS_VERCEL,
        "warning": "Using ephemeral storage. Data will be lost between deployments." if IS_VERCEL else None
    }

# Initialize directories
ensure_dirs()

