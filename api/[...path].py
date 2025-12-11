"""
Catch-all route handler for all API endpoints
Routes all /api/* requests to the FastAPI application
"""
import os
import sys
import logging
from pathlib import Path

# Setup logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
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
    
    from backend.main import app
    logger.info("FastAPI app imported successfully")

    # Initialize handler for Vercel
    # Vercel Python functions expect 'handler' to be the entry point
    handler = Mangum(app, lifespan="off")
    logger.info("Handler initialized successfully")

except Exception as e:
    logger.error(f"Failed to initialize handler: {e}", exc_info=True)
    # Create a minimal error handler
    def error_handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": f'{{"error": "Initialization failed: {str(e)}"}}'
        }
    handler = error_handler

