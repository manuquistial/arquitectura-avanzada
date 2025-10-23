"""OpenTelemetry instrumentation for all services.

Provides:
- Distributed tracing with traceparent propagation
- Metrics (latency, error rates, cache, queues)
- Logs correlation
- OTLP export to Azure Monitor or stdout
"""

import logging
import os
from typing import Optional
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = logging.getLogger(__name__)


class ObservabilityConfig:
    """OpenTelemetry configuration."""
    
    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        otlp_endpoint: Optional[str] = None,
        use_console: bool = True,
        azure_monitor_connection_string: Optional[str] = None
    ):
        """Initialize observability config.
        
        Args:
            service_name: Service name for telemetry
            service_version: Service version
            otlp_endpoint: OTLP endpoint (e.g., http://localhost:4317)
            use_console: Export to stdout if True
            azure_monitor_connection_string: Azure Monitor connection string
        """
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        self.use_console = use_console or os.getenv("OTEL_USE_CONSOLE", "true").lower() == "true"
        self.azure_monitor_connection_string = (
            azure_monitor_connection_string or 
            os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        )
        
        # Resource attributes
        self.resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            "cloud.provider": "azure",
            "cloud.region": os.getenv("AZURE_REGION", "eastus")
        })


def setup_tracing(config: ObservabilityConfig) -> trace.Tracer:
    """Setup distributed tracing.
    
    Args:
        config: Observability configuration
        
    Returns:
        Tracer instance
    """
    # Create tracer provider
    tracer_provider = TracerProvider(resource=config.resource)
    
    # Add exporters
    if config.otlp_endpoint:
        logger.info(f"📊 Configuring OTLP trace exporter: {config.otlp_endpoint}")
        otlp_exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint, insecure=True)
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    if config.use_console:
        logger.info("📊 Configuring console trace exporter (stdout)")
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Azure Monitor (if configured)
    if config.azure_monitor_connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
            logger.info("📊 Configuring Azure Monitor trace exporter")
            azure_exporter = AzureMonitorTraceExporter(
                connection_string=config.azure_monitor_connection_string
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(azure_exporter))
        except ImportError:
            logger.warning("⚠️  azure-monitor-opentelemetry-exporter not installed")
    
    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # Get tracer
    tracer = trace.get_tracer(config.service_name, config.service_version)
    
    logger.info(f"✅ Tracing configured for {config.service_name}")
    return tracer


def setup_metrics(config: ObservabilityConfig) -> metrics.Meter:
    """Setup metrics collection.
    
    Args:
        config: Observability configuration
        
    Returns:
        Meter instance
    """
    # Create metric readers
    readers = []
    
    if config.otlp_endpoint:
        logger.info(f"📊 Configuring OTLP metric exporter: {config.otlp_endpoint}")
        otlp_exporter = OTLPMetricExporter(endpoint=config.otlp_endpoint, insecure=True)
        readers.append(PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=10000))
    
    if config.use_console:
        logger.info("📊 Configuring console metric exporter (stdout)")
        console_exporter = ConsoleMetricExporter()
        readers.append(PeriodicExportingMetricReader(console_exporter, export_interval_millis=60000))
    
    # Azure Monitor (if configured)
    if config.azure_monitor_connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter
            logger.info("📊 Configuring Azure Monitor metric exporter")
            azure_exporter = AzureMonitorMetricExporter(
                connection_string=config.azure_monitor_connection_string
            )
            readers.append(PeriodicExportingMetricReader(azure_exporter, export_interval_millis=60000))
        except ImportError:
            logger.warning("⚠️  azure-monitor-opentelemetry-exporter not installed")
    
    # Create meter provider
    meter_provider = MeterProvider(resource=config.resource, metric_readers=readers)
    metrics.set_meter_provider(meter_provider)
    
    # Get meter
    meter = metrics.get_meter(config.service_name, config.service_version)
    
    logger.info(f"✅ Metrics configured for {config.service_name}")
    return meter


def instrument_fastapi(app, config: ObservabilityConfig):
    """Instrument FastAPI application.
    
    Args:
        app: FastAPI application
        config: Observability configuration
    """
    logger.info("🔧 Instrumenting FastAPI...")
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
        meter_provider=metrics.get_meter_provider(),
        excluded_urls="/health,/metrics,/docs,/openapi.json"
    )


def instrument_httpx():
    """Instrument httpx client for external HTTP calls."""
    logger.info("🔧 Instrumenting httpx...")
    # Temporarily disabled due to httpx base_url=None issue
    # HTTPXClientInstrumentor().instrument()
    logger.info("⚠️  HTTPX instrumentation disabled")


def instrument_redis():
    """Instrument Redis client."""
    logger.info("🔧 Instrumenting Redis...")
    try:
        RedisInstrumentor().instrument()
    except Exception as e:
        logger.warning(f"⚠️  Failed to instrument Redis: {e}")


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy engine.
    
    Args:
        engine: SQLAlchemy engine
    """
    logger.info("🔧 Instrumenting SQLAlchemy...")
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
    except Exception as e:
        logger.warning(f"⚠️  Failed to instrument SQLAlchemy: {e}")


class ServiceMetrics:
    """Standard metrics for all services."""
    
    def __init__(self, meter: metrics.Meter, service_name: str):
        """Initialize service metrics.
        
        Args:
            meter: OpenTelemetry meter
            service_name: Service name
        """
        self.meter = meter
        self.service_name = service_name
        
        # HTTP metrics
        self.http_request_duration = meter.create_histogram(
            name="http.server.request.duration",
            description="HTTP request duration in seconds",
            unit="s"
        )
        
        self.http_request_count = meter.create_counter(
            name="http.server.request.count",
            description="Total HTTP requests",
            unit="1"
        )
        
        self.http_error_count = meter.create_counter(
            name="http.server.error.count",
            description="HTTP errors (5xx)",
            unit="1"
        )
        
        # Cache metrics
        self.cache_hits = meter.create_counter(
            name="cache.hits",
            description="Cache hits",
            unit="1"
        )
        
        self.cache_misses = meter.create_counter(
            name="cache.misses",
            description="Cache misses",
            unit="1"
        )
        
        # Queue metrics
        self.queue_message_published = meter.create_counter(
            name="queue.message.published",
            description="Messages published to queue",
            unit="1"
        )
        
        self.queue_message_consumed = meter.create_counter(
            name="queue.message.consumed",
            description="Messages consumed from queue",
            unit="1"
        )
        
        self.queue_message_failed = meter.create_counter(
            name="queue.message.failed",
            description="Failed message processing",
            unit="1"
        )
        
        self.dlq_length = meter.create_observable_gauge(
            name="queue.dlq.length",
            description="Dead letter queue length",
            unit="1",
            callbacks=[self._get_dlq_length]
        )
        
        # Rate limit metrics
        self.rate_limit_exceeded = meter.create_counter(
            name="rate_limit.exceeded",
            description="Rate limit exceeded count",
            unit="1"
        )
        
        # External call metrics
        self.external_call_duration = meter.create_histogram(
            name="external.call.duration",
            description="External API call duration",
            unit="s"
        )
        
        self.external_call_errors = meter.create_counter(
            name="external.call.errors",
            description="External API call errors",
            unit="1"
        )
        
    def _get_dlq_length(self, options):
        """Callback to get DLQ length (override in subclass)."""
        # This should be implemented by each service
        # For now, return 0
        yield metrics.Observation(0, {})
    
    def record_http_request(self, duration: float, method: str, path: str, status: int):
        """Record HTTP request metrics."""
        attributes = {
            "http.method": method,
            "http.route": path,
            "http.status_code": status
        }
        
        self.http_request_duration.record(duration, attributes)
        self.http_request_count.add(1, attributes)
        
        if status >= 500:
            self.http_error_count.add(1, attributes)
    
    def record_cache_hit(self, cache_key: str):
        """Record cache hit."""
        self.cache_hits.add(1, {"cache.key": cache_key[:32]})
    
    def record_cache_miss(self, cache_key: str):
        """Record cache miss."""
        self.cache_misses.add(1, {"cache.key": cache_key[:32]})
    
    def record_queue_publish(self, queue_name: str):
        """Record message published to queue."""
        self.queue_message_published.add(1, {"queue.name": queue_name})
    
    def record_queue_consume(self, queue_name: str, success: bool):
        """Record message consumed from queue."""
        attributes = {"queue.name": queue_name}
        
        if success:
            self.queue_message_consumed.add(1, attributes)
        else:
            self.queue_message_failed.add(1, attributes)
    
    def record_rate_limit_exceeded(self, route: str, client_ip: str):
        """Record rate limit exceeded."""
        self.rate_limit_exceeded.add(1, {
            "http.route": route,
            "client.ip": client_ip
        })
    
    def record_external_call(self, duration: float, service: str, endpoint: str, success: bool):
        """Record external API call."""
        attributes = {
            "external.service": service,
            "external.endpoint": endpoint,
            "external.success": success
        }
        
        self.external_call_duration.record(duration, attributes)
        
        if not success:
            self.external_call_errors.add(1, attributes)


def setup_observability(
    app,
    service_name: str,
    service_version: str = "1.0.0",
    engine=None
) -> tuple[trace.Tracer, metrics.Meter, ServiceMetrics]:
    """Setup complete observability for a service.
    
    Args:
        app: FastAPI application
        service_name: Service name
        service_version: Service version
        engine: Optional SQLAlchemy engine
        
    Returns:
        Tuple of (tracer, meter, service_metrics)
    """
    logger.info(f"🚀 Setting up observability for {service_name}...")
    
    # Create config
    config = ObservabilityConfig(service_name, service_version)
    
    # Setup tracing
    tracer = setup_tracing(config)
    
    # Setup metrics
    meter = setup_metrics(config)
    
    # Instrument FastAPI
    instrument_fastapi(app, config)
    
    # Instrument httpx
    instrument_httpx()
    
    # Instrument Redis
    instrument_redis()
    
    # Instrument SQLAlchemy (if engine provided)
    if engine:
        instrument_sqlalchemy(engine)
    
    # Create service metrics
    service_metrics = ServiceMetrics(meter, service_name)
    
    logger.info(f"✅ Observability fully configured for {service_name}")
    
    return tracer, meter, service_metrics

