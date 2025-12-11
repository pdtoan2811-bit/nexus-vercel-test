"""
Catch-all route handler for all API endpoints
Routes all /api/* requests to the FastAPI application
"""
import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict

# Setup logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend directory to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
    logger.info(f"Added backend path: {backend_path}")

# Also add current directory for imports
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))
    logger.info(f"Added root path: {root_path}")

# Import after path setup
from mangum import Mangum
logger.info("Mangum imported successfully")

# Import app - this will trigger initialization
try:
    from backend.main import app
    logger.info("FastAPI app imported successfully")
except Exception as import_error:
    logger.error(f"Failed to import app: {import_error}", exc_info=True)
    # Create a minimal error app
    from fastapi import FastAPI
    app = FastAPI()
    @app.get("/{full_path:path}")
    @app.post("/{full_path:path}")
    @app.put("/{full_path:path}")
    @app.delete("/{full_path:path}")
    def error_endpoint(full_path: str):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "error": "Application initialization failed",
                "detail": str(import_error),
                "path": full_path
            }
        )

# Initialize Mangum handler
_mangum_handler = None
try:
    _mangum_handler = Mangum(app, lifespan="off", text_mime_types=False)
    logger.info("Handler initialized successfully")
except Exception as handler_error:
    logger.error(f"Failed to create Mangum handler: {handler_error}", exc_info=True)
    _mangum_handler = None

# Define handler function at module level - must be simple for Vercel validation
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Vercel serverless function handler - module level function"""
    if _mangum_handler is None:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": '{"error": "Handler not initialized"}'
        }
    try:
        result = _mangum_handler(event, context)
        return result
    except Exception as e:
        logger.error(f"Handler execution error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": f'{{"error": "Handler execution failed: {str(e)}"}}'
        }

