"""
Catch-all route handler for all API endpoints
Routes all /api/* requests to the FastAPI application
"""
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Also add current directory for imports
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from mangum import Mangum
from backend.main import app

# Initialize handler for Vercel
# Vercel Python functions expect 'handler' to be the entry point
handler = Mangum(app, lifespan="off")

