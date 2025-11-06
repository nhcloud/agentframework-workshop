"""
Content Safety Service using Azure AI Content Safety.

Monitors and filters content for:
- Hate Speech
- Sexual Content
- Violence
- Self-Harm
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Result of content safety analysis."""
    is_safe: bool
    categories: Dict[str, int]  # {hate: 0, sexual: 0, violence: 0, self_harm: 0}
    severity: int  # Highest severity across all categories
    flagged_categories: list[str]  # Categories that exceeded threshold
    reason: str  # Human-readable explanation


class ContentSafetyService:
    """
    Service for analyzing content safety using Azure AI Content Safety.
    
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
        """Initialize the content safety service."""
        self.enabled = settings.CONTENT_SAFETY_ENABLED
        self.threshold = settings.CONTENT_SAFETY_THRESHOLD
        self.block_input = settings.BLOCK_UNSAFE_INPUT
        self.filter_output_enabled = settings.FILTER_UNSAFE_OUTPUT  # Renamed to avoid conflict with method
        
        self.client = None
        
        if self.enabled:
            if not settings.AZURE_CONTENT_SAFETY_ENDPOINT or not settings.AZURE_CONTENT_SAFETY_KEY:
                logger.warning(
                    "Content Safety enabled but credentials not configured. "
                    "Set AZURE_CONTENT_SAFETY_ENDPOINT and AZURE_CONTENT_SAFETY_KEY"
                )
                self.enabled = False
            else:
                try:
                    self.client = ContentSafetyClient(
                        settings.AZURE_CONTENT_SAFETY_ENDPOINT,
                        AzureKeyCredential(settings.AZURE_CONTENT_SAFETY_KEY)
                    )
                    logger.info(
                        f"Content Safety initialized (threshold: {self.threshold}/7, "
                        f"block_input: {self.block_input}, filter_output: {self.filter_output_enabled})"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize Content Safety client: {str(e)}")
                    self.enabled = False
    
    async def analyze_text(self, text: str) -> SafetyResult:
        """
        Analyze text for unsafe content across all categories.
        
        Args:
            text: Text to analyze
            
        Returns:
            SafetyResult with safety analysis
        """
        # If disabled, always return safe
        if not self.enabled or not self.client:
            return SafetyResult(
                is_safe=True,
                categories={"hate": 0, "sexual": 0, "violence": 0, "self_harm": 0},
                severity=0,
                flagged_categories=[],
                reason="Content safety disabled"
            )
        
        # Skip empty or very short text
        if not text or len(text.strip()) < 3:
            return SafetyResult(
                is_safe=True,
                categories={"hate": 0, "sexual": 0, "violence": 0, "self_harm": 0},
                severity=0,
                flagged_categories=[],
                reason="Text too short to analyze"
            )
        
        try:
            # Analyze text with Azure AI Content Safety
            request = AnalyzeTextOptions(text=text)
            response = self.client.analyze_text(request)
            
            # Extract category scores
            categories = {
                "hate": 0,
                "sexual": 0,
                "violence": 0,
                "self_harm": 0
            }
            
            # Map Azure categories to our format
            if hasattr(response, 'categories_analysis'):
                for category_analysis in response.categories_analysis:
                    category_name = category_analysis.category.lower().replace("_", "")
                    
                    # Map category names
                    if "hate" in category_name:
                        categories["hate"] = category_analysis.severity
                    elif "sex" in category_name:
                        categories["sexual"] = category_analysis.severity
                    elif "violence" in category_name:
                        categories["violence"] = category_analysis.severity
                    elif "selfharm" in category_name or "harm" in category_name:
                        categories["self_harm"] = category_analysis.severity
            
            # Find highest severity
            max_severity = max(categories.values())
            
            # Determine if safe based on threshold
            is_safe = max_severity < self.threshold
            
            # Get flagged categories (at or above threshold)
            flagged = [cat for cat, sev in categories.items() if sev >= self.threshold]
            
            # Build reason message
            if not is_safe:
                flagged_names = ", ".join(flagged)
                reason = f"Content flagged for: {flagged_names} (severity: {max_severity}/7)"
            else:
                reason = "Content is safe"
            
            result = SafetyResult(
                is_safe=is_safe,
                categories=categories,
                severity=max_severity,
                flagged_categories=flagged,
                reason=reason
            )
            
            # Log if flagged
            if not is_safe:
                logger.warning(
                    f"🚨 Unsafe content detected: {result.reason} | "
                    f"Details: {categories} | Text preview: {text[:100]}..."
                )
            elif max_severity >= 3:
                # Log moderate content for monitoring
                logger.info(
                    f"⚠️ Moderate content detected: {categories} | "
                    f"Text preview: {text[:100]}..."
                )
            
            return result
            
        except HttpResponseError as e:
            logger.error(f"Azure Content Safety API error: {str(e)}")
            # On error, fail open (allow content) to avoid blocking legitimate requests
            return SafetyResult(
                is_safe=True,
                categories={"hate": 0, "sexual": 0, "violence": 0, "self_harm": 0},
                severity=0,
                flagged_categories=[],
                reason=f"Analysis failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in content safety analysis: {str(e)}")
            # Fail open on unexpected errors
            return SafetyResult(
                is_safe=True,
                categories={"hate": 0, "sexual": 0, "violence": 0, "self_harm": 0},
                severity=0,
                flagged_categories=[],
                reason=f"Analysis error: {str(e)}"
            )
    
    async def check_input_safety(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Check if user input is safe to process.
        
        Args:
            text: User input to check
            
        Returns:
            Tuple of (is_safe, error_message)
            - is_safe: True if safe to process
            - error_message: Error message if unsafe, None if safe
        """
        if not self.block_input:
            return True, None
        
        result = await self.analyze_text(text)
        
        if not result.is_safe:
            error_msg = (
                "🚫 Your request was blocked due to content safety policies.\n\n"
                f"Reason: {result.reason}\n\n"
                "Please rephrase your request in a respectful and appropriate manner."
            )
            return False, error_msg
        
        return True, None
    
    async def filter_output(self, text: str, agent_name: str = "agent") -> str:
        """
        Filter agent output for unsafe content.
        
        Args:
            text: Agent response to filter
            agent_name: Name of the agent (for logging)
            
        Returns:
            Filtered text (original if safe, replacement if unsafe)
        """
        if not self.filter_output_enabled:
            return text
        
        result = await self.analyze_text(text)
        
        if not result.is_safe:
            logger.error(
                f"🚨 Agent '{agent_name}' generated unsafe content! "
                f"{result.reason} | Response filtered."
            )
            return (
                "⚠️ [This response was filtered due to content safety guidelines. "
                "Please contact support if you believe this was an error.]"
            )
        
        return text
    
    def get_safety_summary(self, result: SafetyResult) -> str:
        """Get a human-readable summary of safety analysis."""
        if result.is_safe:
            return "✅ Content is safe"
        
        details = []
        for category, severity in result.categories.items():
            if severity > 0:
                details.append(f"{category}: {severity}/7")
        
        return f"🚨 Unsafe content: {', '.join(details)}"
