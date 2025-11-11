"""
Safety router for content safety scanning endpoints.

Provides endpoints for testing and validating content safety features,
matching the .NET SafetyController implementation.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

from services.content_safety_service import ContentSafetyService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/safety", tags=["safety"])


class TextScanRequest(BaseModel):
    """Request model for text scanning."""
    text: str = Field(..., description="Text to scan for unsafe content")


class TextScanResponse(BaseModel):
    """Response model for text scanning with camelCase for frontend compatibility."""
    model_config = ConfigDict(populate_by_name=True, by_alias=True)
    
    is_safe: bool = Field(..., serialization_alias="isSafe")
    highest_severity: int = Field(..., serialization_alias="highestSeverity")
    highest_category: str | None = Field(None, serialization_alias="highestCategory")
    category_severities: Dict[str, int] = Field(..., serialization_alias="categorySeverities")
    flagged_categories: list[str] = Field(..., serialization_alias="flaggedCategories")
    blocklist_matches: list[str] = Field(..., serialization_alias="blocklistMatches")


class ImageScanResponse(BaseModel):
    """Response model for image scanning with camelCase for frontend compatibility."""
    model_config = ConfigDict(populate_by_name=True, by_alias=True)
    
    is_safe: bool = Field(..., serialization_alias="isSafe")
    highest_severity: int = Field(..., serialization_alias="highestSeverity")
    highest_category: str | None = Field(None, serialization_alias="highestCategory")
    category_severities: Dict[str, int] = Field(..., serialization_alias="categorySeverities")
    flagged_categories: list[str] = Field(..., serialization_alias="flaggedCategories")


@router.post("/scan-text", response_model=TextScanResponse)
async def scan_text(
    request: TextScanRequest,
    app_request: Request
) -> TextScanResponse:
    """
    Scan text content for safety violations.
    
    Analyzes text across all categories (Hate, Sexual, Violence, SelfHarm)
    and returns detailed safety analysis results.
    
    Args:
        request: Text scan request containing text to analyze
        app_request: FastAPI request object for accessing app state
        
    Returns:
        Detailed safety analysis results
        
    Raises:
        HTTPException: If text is empty or service fails
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        # Get content safety service from app state
        content_safety: ContentSafetyService = app_request.app.state.content_safety_service
        
        # Analyze text
        result = await content_safety.analyze_text_async(request.text)
        
        # Return detailed results
        return TextScanResponse(
            is_safe=result.is_safe,
            highest_severity=result.highest_severity,
            highest_category=result.highest_category,
            category_severities=result.category_severities,
            flagged_categories=result.flagged_categories,
            blocklist_matches=result.blocklist_matches
        )
        
    except Exception as e:
        logger.error(f"Error scanning text: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during text scan: {str(e)}"
        )


@router.post("/scan-image", response_model=ImageScanResponse)
async def scan_image(
    file: UploadFile = File(..., description="Image file to scan"),
    app_request: Request = None
) -> ImageScanResponse:
    """
    Scan image content for safety violations.
    
    Analyzes image across all categories (Hate, Sexual, Violence, SelfHarm)
    and returns detailed safety analysis results.
    
    Args:
        file: Uploaded image file
        app_request: FastAPI request object for accessing app state
        
    Returns:
        Detailed safety analysis results
        
    Raises:
        HTTPException: If file is empty or service fails
    """
    if not file or file.size == 0:
        raise HTTPException(status_code=400, detail="Image file is required")
    
    # Validate file size (50 MB limit)
    max_size = 52_428_800  # 50 MB
    if file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {max_size / 1_048_576} MB"
        )
    
    try:
        # Get content safety service from app state
        content_safety: ContentSafetyService = app_request.app.state.content_safety_service
        
        # Read image bytes
        image_bytes = await file.read()
        
        # Analyze image
        result = await content_safety.analyze_image_async(image_bytes)
        
        # Return detailed results
        return ImageScanResponse(
            is_safe=result.is_safe,
            highest_severity=result.highest_severity,
            highest_category=result.highest_category,
            category_severities=result.category_severities,
            flagged_categories=result.flagged_categories
        )
        
    except Exception as e:
        logger.error(f"Error scanning image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during image scan: {str(e)}"
        )


@router.get("/config")
async def get_safety_config(app_request: Request) -> Dict[str, Any]:
    """
    Get current content safety configuration.
    
    Returns configuration details including thresholds, blocklists,
    and enabled features.
    
    Args:
        app_request: FastAPI request object for accessing app state
        
    Returns:
        Configuration details dictionary
    """
    try:
        content_safety: ContentSafetyService = app_request.app.state.content_safety_service
        
        return {
            "enabled": content_safety.enabled,
            "block_unsafe_input": content_safety.block_unsafe_input,
            "filter_unsafe_output": content_safety.filter_unsafe_output,
            "category_thresholds": content_safety.category_thresholds,
            "blocklists": content_safety.blocklists,
            "output_action": content_safety.output_action.value,
            "placeholder_text": content_safety.placeholder_text
        }
        
    except Exception as e:
        logger.error(f"Error getting safety config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
