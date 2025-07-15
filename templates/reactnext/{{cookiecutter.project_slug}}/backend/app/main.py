"""
{{cookiecutter.project_name}} - FastAPI Backend
{{cookiecutter.description}}

Author: {{cookiecutter.author_name}}
Version: {{cookiecutter.version}}
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import time

from app.core.config import settings
from app.core.database import init_db
from app.api.api_v1.api import api_router
from app.core.exceptions import AppException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting {{cookiecutter.project_name}} backend...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    logger.info("🎉 {{cookiecutter.project_name}} backend started successfully")
    
    yield  # Application runs here
    
    logger.info("🛑 Shutting down {{cookiecutter.project_name}} backend...")


# Create FastAPI application
app = FastAPI(
    title="{{cookiecutter.project_name}} API",
    description="{{cookiecutter.description}}",
    version="{{cookiecutter.version}}",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    logger.info(
        f"📥 {request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"📤 {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response


# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application-specific exceptions"""
    logger.error(f"Application error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
        }
    )


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "{{cookiecutter.project_name}}",
        "version": "{{cookiecutter.version}}",
        "timestamp": time.time(),
    }


# Readiness check endpoint
@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint"""
    # Add checks for database, external services, etc.
    return {
        "status": "ready",
        "service": "{{cookiecutter.project_name}}",
        "checks": {
            "database": "healthy",
            # Add more service checks as needed
        },
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {{cookiecutter.project_name}} API",
        "version": "{{cookiecutter.version}}",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )