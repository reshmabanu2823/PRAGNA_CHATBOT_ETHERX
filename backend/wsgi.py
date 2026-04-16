"""
WSGI entry point for production deployment with Gunicorn.

Usage:
    gunicorn -w 4 -b 0.0.0.0:5001 wsgi:app
    
Environment Variables:
    GUNICORN_WORKERS: Number of worker processes (default: 4)
    GUNICORN_THREADS: Number of threads per worker (default: 2)
    GUNICORN_TIMEOUT: Worker timeout in seconds (default: 120)
"""

import os
import sys
import logging

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and initialize the Flask app
from app import app

if __name__ == '__main__':
    logger.error("This WSGI module should be run with a production server like Gunicorn, not directly.")
    logger.error("Use: gunicorn -w 4 -b 0.0.0.0:5001 wsgi:app")
    sys.exit(1)
