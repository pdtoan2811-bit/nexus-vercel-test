"""
Catch-all route handler for all API endpoints
Routes all /api/* requests to the FastAPI application
"""
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from mangum import Mangum
from backend.main import app

# Initialize handler for Vercel
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """AWS Lambda/Vercel handler"""
    return handler(event, context)

