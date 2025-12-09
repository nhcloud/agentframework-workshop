"""
Observability module for Application Insights integration in Python Agent Framework.

This module provides OpenTelemetry tracing capabilities with Azure Monitor (Application Insights) export.
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    
    # Azure Monitor exporter
    try:
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        AZURE_MONITOR_AVAILABLE = True
    except ImportError:
        AZURE_MONITOR_AVAILABLE = False
        
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    AZURE_MONITOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """
    Manager for OpenTelemetry tracing and Application Insights integration.
    """
    
    def __init__(self, service_name: str = "PythonAgentFramework"):
        self.service_name = service_name
        self.tracer: Optional[Any] = None
        self.tracer_provider: Optional[TracerProvider] = None
        self._initialized = False
        
    def initialize(self, connection_string: Optional[str] = None) -> bool:
        """
        Initialize OpenTelemetry with optional Application Insights export.
        
        Args:
            connection_string: Application Insights connection string
            
        Returns:
            True if initialization was successful, False otherwise
        """
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry is not available. Install with: pip install opentelemetry-api opentelemetry-sdk")
            return False
            
        if self._initialized:
            logger.debug("Observability already initialized")
            return True
            
        try:
            # Create resource
            resource = Resource(attributes={
                SERVICE_NAME: self.service_name
            })
            
            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            
            # Always add console exporter for debugging
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
            
            # Add Azure Monitor exporter if connection string is provided
            if connection_string and AZURE_MONITOR_AVAILABLE:
                try:
                    azure_exporter = AzureMonitorTraceExporter(
                        connection_string=connection_string
                    )
                    self.tracer_provider.add_span_processor(
                        BatchSpanProcessor(azure_exporter)
                    )
                    logger.info(f"? Application Insights enabled: {connection_string[:50]}...")
                except Exception as e:
                    logger.error(f"Failed to initialize Azure Monitor exporter: {e}")
            elif connection_string and not AZURE_MONITOR_AVAILABLE:
                logger.warning("Azure Monitor requested but not available. Install with: pip install azure-monitor-opentelemetry-exporter")
            else:
                logger.info("??  Application Insights not configured. Set APPLICATIONINSIGHTS_CONNECTION_STRING to enable telemetry.")
            
            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Auto-instrument HTTP requests
            try:
                RequestsInstrumentor().instrument()
                logger.debug("Instrumented HTTP requests")
            except Exception as e:
                logger.debug(f"Could not instrument requests: {e}")
            
            self._initialized = True
            logger.info(f"Observability initialized for {self.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize observability: {e}")
            return False
    
    @contextmanager
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for creating a span with automatic error handling.
        
        Args:
            name: Name of the span
            attributes: Optional attributes to add to the span
            
        Yields:
            The created span
        """
        if not self._initialized or not self.tracer:
            # If not initialized, just yield None
            yield None
            return
            
        span = self.tracer.start_as_current_span(name)
        try:
            # Add attributes if provided
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            
            yield span
            
            # Mark span as OK if no exception
            span.set_status(trace.Status(trace.StatusCode.OK))
            
        except Exception as e:
            # Record exception and set error status
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()
    
    def instrument_fastapi(self, app):
        """
        Instrument a FastAPI application for automatic tracing.
        
        Args:
            app: FastAPI application instance
        """
        if not self._initialized:
            logger.warning("Observability not initialized, skipping FastAPI instrumentation")
            return
            
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI application instrumented for tracing")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")
    
    def shutdown(self):
        """Shutdown the tracer provider and flush all spans."""
        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
                logger.info("Observability shutdown completed")
            except Exception as e:
                logger.error(f"Error during observability shutdown: {e}")


# Global observability manager instance
_observability_manager: Optional[ObservabilityManager] = None


def get_observability_manager() -> ObservabilityManager:
    """
    Get the global observability manager instance.
    
    Returns:
        The global ObservabilityManager instance
    """
    global _observability_manager
    if _observability_manager is None:
        _observability_manager = ObservabilityManager()
    return _observability_manager


def initialize_observability(connection_string: Optional[str] = None) -> bool:
    """
    Initialize the global observability manager.
    
    Args:
        connection_string: Optional Application Insights connection string
        
    Returns:
        True if initialization was successful, False otherwise
    """
    manager = get_observability_manager()
    return manager.initialize(connection_string)
