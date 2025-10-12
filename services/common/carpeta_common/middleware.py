"""Common middleware for FastAPI services."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(
    app: FastAPI,
    allow_origins: list = None,
    allow_credentials: bool = True,
    allow_methods: list = None,
    allow_headers: list = None
):
    """Add CORS middleware to FastAPI app.
    
    Args:
        app: FastAPI application
        allow_origins: Allowed origins (default: ["*"])
        allow_credentials: Allow credentials
        allow_methods: Allowed HTTP methods (default: ["*"])
        allow_headers: Allowed headers (default: ["*"])
    """
    # Default to localhost if not provided (secure default)
    default_origins = ["http://localhost:3000", "http://localhost:8000"]
    default_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    default_headers = ["Content-Type", "Authorization", "X-Request-ID", "X-Trace-ID"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or default_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods or default_methods,
        allow_headers=allow_headers or default_headers,
    )


def setup_logging(level: int = logging.INFO, format_string: str = None):
    """Configure logging for service.
    
    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

