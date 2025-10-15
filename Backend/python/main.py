"""
FastAPI Application for Microsoft Agent Framework

This module provides a production-ready multi-agent orchestration API
using Microsoft Agent Framework and Azure AI integration.
"""

import asyncio
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from routers import chat, agents
from core.config import settings
from core.logging_config import setup_logging
from services.agent_service import AgentService
from services.session_manager import SessionManager
from services.group_chat_service import GroupChatService

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Agent Framework application...")
    
    # Initialize services
    session_manager = SessionManager()
    agent_service = AgentService()
    group_chat_service = GroupChatService(agent_service, session_manager)
    
    # Store services in app state
    app.state.session_manager = session_manager
    app.state.agent_service = agent_service  
    app.state.group_chat_service = group_chat_service
    
    logger.info("Agent Framework application started successfully")
    yield
    
    logger.info("Shutting down Agent Framework application...")
    # Cleanup services if needed
    await session_manager.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Microsoft Agent Framework API",
    description="A production-ready multi-agent orchestration framework built with Microsoft Agent Framework and Azure AI integration",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/",
    redoc_url="/redoc"
)

# Configure CORS
frontend_urls = [
    settings.FRONTEND_URL,
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://localhost:3001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[url for url in frontend_urls if url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(agents.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )