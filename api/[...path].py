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

    # Initialize handler for Vercel
    # Vercel Python functions expect 'handler' to be the entry point
    try:
        # Use text_mime_types=False to avoid MIME type issues
        mangum_handler = Mangum(app, lifespan="off", text_mime_types=False)
        logger.info("Handler initialized successfully")
        
        # Wrap Mangum handler to ensure it's a proper callable
        # This helps with Vercel's internal handler validation
        def handler(event, context):
            return mangum_handler(event, context)
        
        # Ensure handler has proper attributes for Vercel validation
        handler.__name__ = "handler"
        handler.__module__ = __name__
        
    except Exception as handler_error:
        logger.error(f"Failed to create handler: {handler_error}", exc_info=True)
        # Create fallback handler
        def error_handler(event, context):
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": f'{{"error": "Handler initialization failed: {str(handler_error)}"}}'
            }
        handler = error_handler

except Exception as e:
    logger.error(f"Failed to initialize handler: {e}", exc_info=True)
    import traceback
    error_trace = traceback.format_exc()
    logger.error(f"Full traceback: {error_trace}")
    # Create a minimal error handler
    def error_handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": f'{{"error": "Initialization failed: {str(e)}", "traceback": "{error_trace}"}}'
        }
    handler = error_handler

