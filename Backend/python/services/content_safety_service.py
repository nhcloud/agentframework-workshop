"""
Content Safety Service using Azure AI Content Safety.

Enhanced implementation matching .NET ContentSafetyService features:
- Text and Image analysis
- Per-category thresholds
- Blocklists support
- Multiple output filtering actions
- Comprehensive result tracking

Monitors and filters content for:
- Hate Speech
- Sexual Content
- Violence
- Self-Harm
"""

import logging
import io
from typing import Dict, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import (
    AnalyzeTextOptions, 
    AnalyzeImageOptions,
    ImageData,
    TextCategory
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from core.config import settings


logger = logging.getLogger(__name__)


class OutputAction(str, Enum):
    """Output filtering actions."""
    REDACT = "redact"
    PLACEHOLDER = "placeholder"
    EMPTY = "empty"


@dataclass
class ContentSafetyResult:
    """
    Result of content safety analysis.
    
    Enhanced to match .NET ContentSafetyResult structure with additional metadata.
    """
    enabled: bool = True
    highest_severity: int = 0
    highest_category: Optional[str] = None
    raw: Optional[any] = None  # Raw API response for debugging
    media_type: str = "text"  # "text" or "image"
    category_severities: Dict[str, int] = field(default_factory=dict)
    flagged_categories: List[str] = field(default_factory=list)
    blocklist_matches: List[str] = field(default_factory=list)
    is_safe: bool = True
    error: Optional[str] = None
    reason: str = ""  # Human-readable explanation
    
    @staticmethod
    def not_configured() -> 'ContentSafetyResult':
        """Create a result indicating service is not configured."""
        return ContentSafetyResult(
            enabled=False,
            is_safe=True,
            reason="Content safety not configured"
        )
    
    @staticmethod
    def failure(error_message: str) -> 'ContentSafetyResult':
        """Create a result indicating analysis failure."""
        return ContentSafetyResult(
            enabled=False,
            is_safe=True,  # Fail-open
            error=error_message,
            reason=f"Analysis failed: {error_message}"
        )


# Legacy alias for backward compatibility
SafetyResult = ContentSafetyResult


class ContentSafetyService:
    """
    Enhanced Content Safety Service matching .NET implementation.
    
    Features:
    - Text and Image analysis
    - Per-category thresholds (Hate, SelfHarm, Sexual, Violence)
    - Blocklists support
    - Multiple output filtering actions (redact, placeholder, empty)
    - Comprehensive result tracking
    
    Monitors 4 categories:
    1. Hate Speech - Targeting race, religion, gender, etc.
    2. Sexual Content - Explicit sexual content
    3. Violence - Graphic violence, harm to others
    4. Self-Harm - Suicide, self-injury
    
    Severity Levels (0-7):
    - 0-2: Safe
    - 3-4: Moderate (logged)
    - 5-6: High risk (filtered)
    - 7: Severe (blocked)
    """
    
    def __init__(self):
        """Initialize the content safety service with enhanced configuration."""
        self.enabled = settings.CONTENT_SAFETY_ENABLED
        self.block_unsafe_input = settings.CONTENT_SAFETY_BLOCK_UNSAFE_INPUT
        self.filter_unsafe_output = settings.CONTENT_SAFETY_FILTER_UNSAFE_OUTPUT
        
        # Per-category thresholds (matching .NET)
        self.category_thresholds = {
            "Hate": settings.CONTENT_SAFETY_THRESHOLD_HATE,
            "SelfHarm": settings.CONTENT_SAFETY_THRESHOLD_SELFHARM,
            "Sexual": settings.CONTENT_SAFETY_THRESHOLD_SEXUAL,
            "Violence": settings.CONTENT_SAFETY_THRESHOLD_VIOLENCE
        }
        
        # Blocklists support
        self.blocklists: List[str] = []
        if settings.CONTENT_SAFETY_BLOCKLISTS:
            self.blocklists = [
                bl.strip() for bl in settings.CONTENT_SAFETY_BLOCKLISTS.split(",")
                if bl.strip()
            ]
        
        # Output filtering configuration
        self.output_action = OutputAction(settings.CONTENT_SAFETY_OUTPUT_ACTION.lower())
        self.placeholder_text = settings.CONTENT_SAFETY_PLACEHOLDER_TEXT
        
        self.client: Optional[ContentSafetyClient] = None
        
        if self.enabled:
            if not settings.AZURE_CONTENT_SAFETY_ENDPOINT or not settings.AZURE_CONTENT_SAFETY_KEY:
                logger.warning(
                    "Content Safety enabled but credentials not configured. "
                    "Set CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_API_KEY"
                )
                self.enabled = False
            else:
                try:
                    self.client = ContentSafetyClient(
                        settings.AZURE_CONTENT_SAFETY_ENDPOINT,
                        AzureKeyCredential(settings.AZURE_CONTENT_SAFETY_KEY)
                    )
                    logger.info(
                        f"Content Safety initialized at {settings.AZURE_CONTENT_SAFETY_ENDPOINT}. "
                        f"Thresholds: {self.category_thresholds}, "
                        f"Blocklists: {len(self.blocklists)}, "
                        f"Output action: {self.output_action.value}"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize Content Safety client: {str(e)}")
                    self.enabled = False
    
    def _normalize_category_name(self, category_enum) -> str:
        """
        Normalize category enum to clean category name.
        
        Azure SDK returns TextCategory enum values like:
        - TextCategory.HATE -> "Hate"
        - TextCategory.SELF_HARM -> "SelfHarm"
        - TextCategory.SEXUAL -> "Sexual"
        - TextCategory.VIOLENCE -> "Violence"
        
        Args:
            category_enum: TextCategory enum value
            
        Returns:
            Clean category name matching .NET conventions
        """
        # Get the enum value name (e.g., "HATE", "SELF_HARM")
        category_str = str(category_enum)
        
        # If it has a dot (like "TextCategory.HATE"), extract the part after the dot
        if "." in category_str:
            category_str = category_str.split(".")[-1]
        
        # Convert to title case and handle special cases
        category_str = category_str.lower()
        
        # Map to .NET naming conventions
        category_mapping = {
            "hate": "Hate",
            "self_harm": "SelfHarm",
            "sexual": "Sexual",
            "violence": "Violence"
        }
        
        return category_mapping.get(category_str, category_str.title())
    
    async def analyze_text_async(self, text: str) -> ContentSafetyResult:
        """
        Analyze text for unsafe content across all categories.
        
        Enhanced implementation matching .NET AnalyzeTextAsync with:
        - Per-category threshold evaluation
        - Blocklists support
        - Comprehensive result tracking
        
        Args:
            text: Text to analyze
            
        Returns:
            ContentSafetyResult with detailed safety analysis
        """
        # If disabled, return not configured
        if not self.enabled or not self.client:
            return ContentSafetyResult.not_configured()
        
        # Skip empty or whitespace-only text
        if not text or not text.strip():
            return ContentSafetyResult.not_configured()
        
        try:
            # Prepare analysis request
            # According to Azure SDK docs, AnalyzeTextOptions takes text as required param
            # and optional blocklist_names and categories parameters
            request = AnalyzeTextOptions(text=text)
            
            # Add blocklists if configured (must be a list)
            if self.blocklists and len(self.blocklists) > 0:
                request.blocklist_names = self.blocklists
            
            # Call Azure Content Safety API (sync call, but wrapped in async function)
            response = self.client.analyze_text(request)
            
            # Build result from response
            return self._build_result_from_text(response, text)
            
        except HttpResponseError as e:
            logger.error(f"Azure Content Safety API error: {str(e)}")
            return ContentSafetyResult.failure(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in content safety analysis: {str(e)}", exc_info=True)
            return ContentSafetyResult.failure(str(e))
    
    async def analyze_image_async(self, image_data: Union[bytes, io.BytesIO]) -> ContentSafetyResult:
        """
        Analyze image for unsafe content.
        
        New method matching .NET AnalyzeImageAsync functionality.
        
        Args:
            image_data: Image bytes or BytesIO stream
            
        Returns:
            ContentSafetyResult with image safety analysis
        """
        # If disabled, return not configured
        if not self.enabled or not self.client:
            return ContentSafetyResult.not_configured()
        
        try:
            # Convert to bytes if needed
            if isinstance(image_data, io.BytesIO):
                image_bytes = image_data.getvalue()
            else:
                image_bytes = image_data
            
            if not image_bytes:
                return ContentSafetyResult.not_configured()
            
            # Prepare image analysis request
            # According to Azure SDK docs, ImageData wraps the binary content
            from azure.core.rest import HttpRequest
            image = ImageData(content=image_bytes)
            request = AnalyzeImageOptions(image=image)
            
            # Call Azure Content Safety API (sync call, wrapped in async)
            response = self.client.analyze_image(request)
            
            # Build result from response
            return self._build_result_from_image(response)
            
        except HttpResponseError as e:
            logger.error(f"Azure Content Safety image API error: {str(e)}")
            return ContentSafetyResult.failure(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in image safety analysis: {str(e)}", exc_info=True)
            return ContentSafetyResult.failure(str(e))
    
    def _build_result_from_text(self, response: any, original_text: str) -> ContentSafetyResult:
        """
        Build ContentSafetyResult from text analysis response.
        
        Matches .NET BuildResult method logic.
        Response structure from Azure SDK:
        - categories_analysis: list of TextCategoriesAnalysis
        - blocklists_match: list of TextBlocklistMatch (optional)
        """
        highest_severity = 0
        highest_category = None
        category_severities: Dict[str, int] = {}
        flagged_categories: List[str] = []
        blocklist_matches: List[str] = []
        
        # Process category analysis
        # Response has categories_analysis attribute with list of results
        if hasattr(response, 'categories_analysis') and response.categories_analysis:
            for category_analysis in response.categories_analysis:
                # category_analysis has 'category' (enum) and 'severity' (int) attributes
                # Extract clean category name from enum (e.g., "Hate", "Sexual", "Violence", "SelfHarm")
                category_enum = category_analysis.category
                category_name = self._normalize_category_name(category_enum)
                severity = int(category_analysis.severity) if category_analysis.severity is not None else 0
                
                category_severities[category_name] = severity
                
                # Track highest severity
                if severity > highest_severity:
                    highest_severity = severity
                    highest_category = category_name
                
                # Check against per-category threshold
                threshold = self.category_thresholds.get(category_name, 5)
                if threshold != -1 and severity >= threshold:
                    flagged_categories.append(category_name)
        
        # Process blocklist matches (optional, may not be present)
        if hasattr(response, 'blocklists_match') and response.blocklists_match:
            for blocklist_match in response.blocklists_match:
                # Each match has blocklist_name and blocklist_item_text
                if hasattr(blocklist_match, 'blocklist_item_text') and blocklist_match.blocklist_item_text:
                    blocklist_matches.append(str(blocklist_match.blocklist_item_text))
        
        # Determine if safe
        is_safe = len(flagged_categories) == 0 and len(blocklist_matches) == 0
        
        # Build reason
        if not is_safe:
            reasons = []
            if flagged_categories:
                reasons.append(f"Categories: {', '.join(flagged_categories)}")
            if blocklist_matches:
                reasons.append(f"Blocklist matches: {len(blocklist_matches)}")
            reason = f"Content flagged - {'; '.join(reasons)}"
        else:
            reason = "Content is safe"
        
        # Log unsafe content
        if not is_safe:
            logger.warning(
                f"Unsafe content detected: {reason} | "
                f"Severities: {category_severities} | "
                f"Text preview: {original_text[:100]}..."
            )
        
        return ContentSafetyResult(
            enabled=True,
            highest_severity=highest_severity,
            highest_category=highest_category,
            raw=response,
            media_type="text",
            category_severities=category_severities,
            flagged_categories=flagged_categories,
            blocklist_matches=blocklist_matches,
            is_safe=is_safe,
            reason=reason
        )
    
    def _build_result_from_image(self, response: any) -> ContentSafetyResult:
        """
        Build ContentSafetyResult from image analysis response.
        
        Matches .NET BuildResult method logic for images.
        Image response has same structure as text: categories_analysis list
        """
        highest_severity = 0
        highest_category = None
        category_severities: Dict[str, int] = {}
        flagged_categories: List[str] = []
        
        # Process category analysis (same structure as text response)
        if hasattr(response, 'categories_analysis') and response.categories_analysis:
            for category_analysis in response.categories_analysis:
                category_enum = category_analysis.category
                category_name = self._normalize_category_name(category_enum)
                severity = int(category_analysis.severity) if category_analysis.severity is not None else 0
                
                category_severities[category_name] = severity
                
                # Track highest severity
                if severity > highest_severity:
                    highest_severity = severity
                    highest_category = category_name
                
                # Check against per-category threshold
                threshold = self.category_thresholds.get(category_name, 5)
                if threshold != -1 and severity >= threshold:
                    flagged_categories.append(category_name)
        
        # Determine if safe
        is_safe = len(flagged_categories) == 0
        
        # Build reason
        reason = "Image is safe" if is_safe else f"Image flagged for: {', '.join(flagged_categories)}"
        
        # Log unsafe images
        if not is_safe:
            logger.warning(f"Unsafe image detected: {reason} | Severities: {category_severities}")
        
        return ContentSafetyResult(
            enabled=True,
            highest_severity=highest_severity,
            highest_category=highest_category,
            raw=response,
            media_type="image",
            category_severities=category_severities,
            flagged_categories=flagged_categories,
            blocklist_matches=[],
            is_safe=is_safe,
            reason=reason
        )
    
    def is_safe(self, result: ContentSafetyResult) -> bool:
        """
        Check if content is safe based on analysis result.
        
        Matches .NET IsSafe method.
        
        Args:
            result: Content safety analysis result
            
        Returns:
            True if safe, False if unsafe
        """
        if not result.enabled:
            return True  # Not configured or errored: treat as safe
        return result.is_safe
    
    async def check_user_input_async(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user input is safe to process.
        
        Matches .NET CheckUserInputAsync method.
        
        Args:
            text: User input to check
            
        Returns:
            Tuple of (is_allowed, error_message)
            - is_allowed: True if safe to process
            - error_message: Error message if unsafe, None if safe
        """
        if not self.enabled or not self.block_unsafe_input:
            return True, None
        
        result = await self.analyze_text_async(text)
        
        if not self.is_safe(result):
            error_msg = f"Input blocked due to unsafe content: {', '.join(result.flagged_categories)}"
            return False, error_msg
        
        return True, None
    
    def filter_output(self, original: str, analysis: ContentSafetyResult) -> str:
        """
        Filter output text based on safety analysis.
        
        Matches .NET FilterOutput method with configurable actions.
        
        Args:
            original: Original text to filter
            analysis: Safety analysis result
            
        Returns:
            Filtered text based on output_action configuration
        """
        if not self.enabled or not self.filter_unsafe_output:
            return original
        
        if self.is_safe(analysis):
            return original
        
        # Apply configured output action
        if self.output_action == OutputAction.PLACEHOLDER:
            return self.placeholder_text
        elif self.output_action == OutputAction.EMPTY:
            return ""
        else:  # REDACT (default)
            return self._redact_unsafe(original, analysis)
    
    def _redact_unsafe(self, original: str, analysis: ContentSafetyResult) -> str:
        """
        Redact unsafe content from text.
        
        Simple strategy: replace entire content.
        Could be enhanced with granular redaction in the future.
        
        Args:
            original: Original text
            analysis: Safety analysis result
            
        Returns:
            Redacted text
        """
        return self.placeholder_text
    
    # Legacy methods for backward compatibility
    
    async def analyze_text(self, text: str) -> ContentSafetyResult:
        """
        Legacy method - calls analyze_text_async.
        
        Maintained for backward compatibility.
        """
        return await self.analyze_text_async(text)
    
    async def check_input_safety(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Legacy method - calls check_user_input_async.
        
        Maintained for backward compatibility.
        """
        return await self.check_user_input_async(text)
    
    async def filter_output_async(self, text: str, agent_name: str = "agent") -> str:
        """
        Async wrapper for filter_output with analysis.
        
        Args:
            text: Agent response to filter
            agent_name: Name of the agent (for logging)
            
        Returns:
            Filtered text
        """
        result = await self.analyze_text_async(text)
        
        if not self.is_safe(result):
            logger.error(
                f"Agent '{agent_name}' generated unsafe content! "
                f"{result.reason} | Response filtered."
            )
        
        return self.filter_output(text, result)
    
    def get_safety_summary(self, result: ContentSafetyResult) -> str:
        """
        Get a human-readable summary of safety analysis.
        
        Args:
            result: Content safety analysis result
            
        Returns:
            Human-readable summary string
        """
        if result.is_safe:
            return "✅ Content is safe"
        
        details = []
        for category, severity in result.category_severities.items():
            if severity > 0:
                details.append(f"{category}: {severity}/7")
        
        if result.blocklist_matches:
            details.append(f"Blocklist matches: {len(result.blocklist_matches)}")
        
        return f"🚨 Unsafe content: {', '.join(details)}"
