"""
Main FastAPI application entry point.

This module initializes the FastAPI application and configures:
- CORS middleware
- Rate limiting
- API routes
- Error handlers
- Logging
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Import routes
from routes import config_routes, chat_routes, session_routes, prompt_routes, graph_routes, graph_viewer_routes, export_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("application_startup", environment=os.getenv("ENVIRONMENT", "development"))
    
    # Initialize data directories
    data_dir = os.getenv("DATA_DIR", "./data")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "conversations"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "sessions"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "vectors"), exist_ok=True)
    
    yield
    
    logger.info("application_shutdown")


# Initialize FastAPI app
app = FastAPI(
    title="Product Investigator Chatbot API",
    description="LLM-powered chatbot for investigating product ideas and generating development prompts",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Product Investigator Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Register API routes
app.include_router(config_routes.router)
app.include_router(chat_routes.router)
app.include_router(session_routes.router)
app.include_router(prompt_routes.router)
app.include_router(graph_routes.router)
app.include_router(graph_viewer_routes.router)
app.include_router(export_routes.router)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
