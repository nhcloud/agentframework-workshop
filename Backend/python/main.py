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

from routers import chat, agents, safety
from routers import mcp, demo  # New MCP and Demo routers
from core.config import settings
from core.logging_config import setup_logging
from core.observability import initialize_observability, get_observability_manager
from services.agent_service_new import AgentService
from services.agent_instructions_service import AgentInstructionsService
from services.session_manager import SessionManager
from services.workflow_orchestration_service import WorkflowOrchestrationService
from services.content_safety_service import ContentSafetyService
from services.mcp_client_service import McpClientService
from services.mcp_tool_function_factory import McpToolFunctionFactory

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Agent Framework application...")
    
    # Initialize observability with Application Insights
    app_insights_connection = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    observability_initialized = initialize_observability(app_insights_connection)
    
    if observability_initialized:
        logger.info("? Observability initialized successfully")
        # Instrument FastAPI for automatic tracing
        get_observability_manager().instrument_fastapi(app)
    else:
        logger.warning("??  Observability not initialized - telemetry will be limited")
    
    # Initialize services (matches .NET Program.cs service registration pattern)
    session_manager = SessionManager()
    instructions_service = AgentInstructionsService()
    agent_service = AgentService()
    content_safety_service = ContentSafetyService()
    
    # Initialize MCP services (matches .NET MCP implementation)
    mcp_client_service = McpClientService()
    mcp_tool_factory = McpToolFunctionFactory(mcp_client_service)
    
    workflow_service = WorkflowOrchestrationService(
        agent_service, 
        session_manager,
        content_safety_service=content_safety_service
    )
    
    # Store services in app state (similar to .NET DI container)
    app.state.session_manager = session_manager
    app.state.instructions_service = instructions_service
    app.state.agent_service = agent_service  
    app.state.workflow_service = workflow_service
    app.state.content_safety_service = content_safety_service
    app.state.observability_manager = get_observability_manager()
    
    # MCP services
    app.state.mcp_client_service = mcp_client_service
    app.state.mcp_tool_factory = mcp_tool_factory
    
    # Log MCP configuration
    try:
        servers = await mcp_client_service.get_configured_servers()
        logger.info(f"MCP Client Service: Initialized with {len(servers)} servers")
        for server in servers:
            logger.info(f"  - {server.name} ({server.transport}): {'enabled' if server.enabled else 'disabled'}")
    except Exception as ex:
        logger.warning(f"Could not enumerate MCP servers: {str(ex)}")
    
    logger.info("Agent Framework application started successfully")
    logger.info(f"Content Safety: {'Enabled' if content_safety_service.enabled else 'Disabled'}")
    
    yield
    
    logger.info("Shutting down Agent Framework application...")
    # Cleanup services
    await session_manager.cleanup()
    await mcp_client_service.close()
    
    # Shutdown observability
    get_observability_manager().shutdown()


# Create FastAPI app
app = FastAPI(
    title="Microsoft Agent Framework API",
    description="A production-ready multi-agent orchestration framework built with Microsoft Agent Framework and Azure AI integration. Includes MCP (Model Context Protocol) support for external tool integration.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/",
    redoc_url="/redoc"
)

# Configure CORS
frontend_urls = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
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
app.include_router(safety.router)
app.include_router(mcp.router)  # MCP management endpoints
app.include_router(demo.router)  # Demo API endpoints


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "framework": "Python FastAPI",
        "features": ["chat", "agents", "safety", "mcp", "demo"]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# For running directly with python main.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)