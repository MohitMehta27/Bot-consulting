"""
Main FastAPI application entry point
"""
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import db
from app.utils.logger import setup_logging
from app.api.v1 import conversations, messages, documents
import os

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BOT GPT API",
    description="Conversational AI Platform Backend",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        db.connect()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    try:
        db.close()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serves chatbot interface"""
    try:
        # Get the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        html_path = os.path.join(project_root, "index.html")
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error loading chatbot HTML: {e}")
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>BOT GPT</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>BOT GPT API</h1>
            <p>Error loading chatbot interface: {str(e)}</p>
            <p><a href="/docs">API Documentation</a></p>
        </body>
        </html>
        """)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute_query("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
