"""Azure Application Insights monitoring and telemetry for read models service."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AzureApplicationInsights:
    """Azure Application Insights client with error handling."""
    
    def __init__(self, settings):
        self.settings = settings
        self.tracer = None
        self.metrics = None
        self.connected = False
        
        # Initialize Application Insights client
        try:
            from opencensus.ext.azure import metrics_exporter
            from opencensus.ext.azure.log_exporter import AzureLogHandler
            from opencensus.trace import tracer as trace_tracer
            from opencensus.trace.samplers import ProbabilitySampler
            
            # Application Insights configuration
            if settings.is_azure_environment():
                # Azure Application Insights configuration
                self.connection_string = settings.app_insights_connection_string
                
                if self.connection_string:
                    # Initialize metrics exporter
                    self.metrics = metrics_exporter.new_metrics_exporter(
                        connection_string=self.connection_string
                    )
                    
                    # Initialize tracer
                    self.tracer = trace_tracer.Tracer(
                        sampler=ProbabilitySampler(rate=1.0)
                    )
                    
                    # Initialize log handler
                    self.log_handler = AzureLogHandler(
                        connection_string=self.connection_string
                    )
                    
                    # Add handler to logger
                    logger.addHandler(self.log_handler)
                    
                    self.connected = True
                    logger.info("✅ Azure Application Insights initialized")
                else:
                    logger.warning("⚠️ Application Insights connection string not configured")
                    self.connected = False
            else:
                logger.info("💡 Running in local mode - Application Insights disabled")
                self.connected = False
                
        except ImportError:
            logger.error("❌ opencensus-ext-azure not installed")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Application Insights: {e}")
            self.connected = False
    
    def track_event(self, name: str, properties: Optional[Dict[str, Any]] = None, 
                   measurements: Optional[Dict[str, float]] = None):
        """Track custom event."""
        if not self.connected or not self.metrics:
            return
        
        try:
            if properties is None:
                properties = {}
            if measurements is None:
                measurements = {}
            
            # Add service context
            properties.update({
                "service": "read-models",
                "environment": self.settings.environment,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            self.metrics.record_event(name, properties, measurements)
            logger.debug(f"📊 Tracked event: {name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track event {name}: {e}")
    
    def track_metric(self, name: str, value: float, properties: Optional[Dict[str, Any]] = None):
        """Track custom metric."""
        if not self.connected or not self.metrics:
            return
        
        try:
            if properties is None:
                properties = {}
            
            # Add service context
            properties.update({
                "service": "read-models",
                "environment": self.settings.environment
            })
            
            self.metrics.record_metric(name, value, properties)
            logger.debug(f"📊 Tracked metric: {name} = {value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track metric {name}: {e}")
    
    def track_dependency(self, name: str, data: str, type_name: str, 
                        success: bool, duration_ms: float, 
                        properties: Optional[Dict[str, Any]] = None):
        """Track dependency call."""
        if not self.connected or not self.metrics:
            return
        
        try:
            if properties is None:
                properties = {}
            
            # Add service context
            properties.update({
                "service": "read-models",
                "environment": self.settings.environment,
                "success": success,
                "duration_ms": duration_ms
            })
            
            self.metrics.record_dependency(name, data, type_name, success, duration_ms, properties)
            logger.debug(f"📊 Tracked dependency: {name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track dependency {name}: {e}")
    
    def track_exception(self, exception: Exception, properties: Optional[Dict[str, Any]] = None):
        """Track exception."""
        if not self.connected or not self.metrics:
            return
        
        try:
            if properties is None:
                properties = {}
            
            # Add service context
            properties.update({
                "service": "read-models",
                "environment": self.settings.environment,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            })
            
            self.metrics.record_exception(exception, properties)
            logger.debug(f"📊 Tracked exception: {type(exception).__name__}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track exception: {e}")
    
    def start_trace(self, name: str, properties: Optional[Dict[str, Any]] = None):
        """Start distributed trace."""
        if not self.connected or not self.tracer:
            return None
        
        try:
            if properties is None:
                properties = {}
            
            # Add service context
            properties.update({
                "service": "read-models",
                "environment": self.settings.environment
            })
            
            span = self.tracer.start_span(name)
            span.add_attribute("service", "read-models")
            span.add_attribute("environment", self.settings.app.environment)
            
            for key, value in properties.items():
                span.add_attribute(key, str(value))
            
            logger.debug(f"📊 Started trace: {name}")
            return span
            
        except Exception as e:
            logger.error(f"❌ Failed to start trace {name}: {e}")
            return None
    
    def end_trace(self, span, success: bool = True, properties: Optional[Dict[str, Any]] = None):
        """End distributed trace."""
        if not span:
            return
        
        try:
            if properties is None:
                properties = {}
            
            span.add_attribute("success", success)
            for key, value in properties.items():
                span.add_attribute(key, str(value))
            
            span.end()
            logger.debug("📊 Ended trace")
            
        except Exception as e:
            logger.error(f"❌ Failed to end trace: {e}")
    
    def track_query_performance(self, query_type: str, duration_ms: float, 
                              record_count: int, cache_hit: bool = False):
        """Track query performance metrics."""
        self.track_metric(
            "query_duration_ms",
            duration_ms,
            {
                "query_type": query_type,
                "record_count": record_count,
                "cache_hit": cache_hit
            }
        )
        
        self.track_metric(
            "query_records_returned",
            record_count,
            {
                "query_type": query_type,
                "cache_hit": cache_hit
            }
        )
    
    def track_cache_performance(self, operation: str, success: bool, duration_ms: float):
        """Track cache performance metrics."""
        self.track_metric(
            "cache_operation_duration_ms",
            duration_ms,
            {
                "operation": operation,
                "success": success
            }
        )
        
        self.track_metric(
            "cache_operation_success",
            1 if success else 0,
            {
                "operation": operation
            }
        )
    
    def track_event_processing(self, event_type: str, success: bool, duration_ms: float):
        """Track event processing performance."""
        self.track_metric(
            "event_processing_duration_ms",
            duration_ms,
            {
                "event_type": event_type,
                "success": success
            }
        )
        
        self.track_metric(
            "event_processing_success",
            1 if success else 0,
            {
                "event_type": event_type
            }
        )
    
    def track_database_operation(self, operation: str, table: str, success: bool, 
                               duration_ms: float, record_count: int = 0):
        """Track database operation metrics."""
        self.track_metric(
            "database_operation_duration_ms",
            duration_ms,
            {
                "operation": operation,
                "table": table,
                "success": success,
                "record_count": record_count
            }
        )
        
        self.track_metric(
            "database_operation_success",
            1 if success else 0,
            {
                "operation": operation,
                "table": table
            }
        )


# Global Application Insights instance
app_insights = None


def get_app_insights(settings) -> Optional[AzureApplicationInsights]:
    """Get or create Application Insights instance."""
    global app_insights
    
    if app_insights is None:
        app_insights = AzureApplicationInsights(settings)
    
    return app_insights if app_insights.connected else None
