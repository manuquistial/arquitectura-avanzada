"""MinTIC Hub HTTP client with intelligent retry logic."""

import asyncio
import hashlib
import logging
import random
import time
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from app.config import Settings
from app.models import (
    AuthenticateDocumentRequest,
    MinTICResponse,
    OperatorInfo,
    RegisterCitizenRequest,
    RegisterOperatorRequest,
    RegisterTransferEndPointRequest,
    UnregisterCitizenRequest,
)
from app.sanitizer import DataSanitizer, AuditLogger
from app.hub_rate_limiter import HubRateLimiter
from app.telemetry import HubTelemetry
from app.redis_client import RedisClient

logger = logging.getLogger(__name__)

# Try to import circuit breaker and observability
try:
    from carpeta_common.circuit_breaker import CircuitBreaker, CircuitBreakerState
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False
    logger.warning("⚠️  Circuit breaker not available")

try:
    from opentelemetry import metrics, trace
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("⚠️  OpenTelemetry not available")


class MinTICClient:
    """HTTP client for MinTIC Hub (public API, no authentication)."""

    def __init__(self, settings: Settings) -> None:
        """Initialize MinTIC client."""
        self.settings = settings
        self.base_url = settings.mintic_base_url

        # Configure HTTP client (GovCarpeta is a public API)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=settings.request_timeout,
            follow_redirects=True,
            verify=False,  # Disable SSL verification for public API
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # Hub rate limiter (protect public hub from saturation)
        self.hub_rate_limiter = HubRateLimiter(
            requests_per_minute=settings.hub_rate_limit_per_minute,
            enabled=settings.hub_rate_limit_enabled
        )
        
        # Redis client for caching
        self.redis_client = RedisClient(settings)
        
        # Circuit breakers per endpoint
        self.circuit_breakers = {}
        if CIRCUIT_BREAKER_AVAILABLE:
            # Create circuit breaker for each hub endpoint
            cb_config = {
                "failure_threshold": 5,      # Open after 5 failures
                "recovery_timeout": 60,      # Try recovery after 60s
                "expected_exception": (httpx.HTTPError,),
                "half_open_max_calls": 3     # Test with 3 calls in half-open
            }
            
            self.circuit_breakers = {
                "registerCitizen": CircuitBreaker(name="hub_registerCitizen", **cb_config),
                "unregisterCitizen": CircuitBreaker(name="hub_unregisterCitizen", **cb_config),
                "authenticateDocument": CircuitBreaker(name="hub_authenticateDocument", **cb_config),
                "validateCitizen": CircuitBreaker(name="hub_validateCitizen", **cb_config),
                "registerOperator": CircuitBreaker(name="hub_registerOperator", **cb_config),
                "registerTransferEndpoint": CircuitBreaker(name="hub_registerTransferEndpoint", **cb_config),
                "getOperators": CircuitBreaker(name="hub_getOperators", **cb_config),
            }
            logger.info("✅ Circuit breakers initialized for all hub endpoints")
        
        # OpenTelemetry tracer and metrics
        self.tracer = None
        self.metrics = None
        if OTEL_AVAILABLE:
            # Tracer for spans
            self.tracer = trace.get_tracer("mintic_client", "1.0.0")
            
            # Metrics
            meter = metrics.get_meter("mintic_client")
            
            self.hub_calls = meter.create_counter(
                name="hub.calls",
                description="Total calls to MinTIC hub",
                unit="1"
            )
            
            self.hub_latency = meter.create_histogram(
                name="hub.latency",
                description="Latency of hub calls in seconds",
                unit="s"
            )
            
            self.hub_success_rate = meter.create_up_down_counter(
                name="hub.success_rate",
                description="Success rate of hub calls",
                unit="1"
            )
            
            self.hub_status_codes = meter.create_counter(
                name="hub.status_codes",
                description="Hub response status codes",
                unit="1"
            )
            
            self.hub_cb_open = meter.create_observable_gauge(
                name="hub.cb_open",
                description="Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
                unit="1",
                callbacks=[self._get_cb_states]
            )
            
            logger.info("✅ OpenTelemetry metrics configured")
    
    def _get_cb_states(self, options):
        """Callback to get circuit breaker states for metrics."""
        if CIRCUIT_BREAKER_AVAILABLE:
            for name, cb in self.circuit_breakers.items():
                state_value = {
                    CircuitBreakerState.CLOSED: 0,
                    CircuitBreakerState.OPEN: 1,
                    CircuitBreakerState.HALF_OPEN: 2
                }.get(cb.state, 0)
                
                yield metrics.Observation(state_value, {"endpoint": name})

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
    
    def _parse_response(self, response: httpx.Response) -> MinTICResponse:
        """Parse hub response into unified DTO.
        
        Args:
            response: httpx Response
            
        Returns:
            MinTICResponse with ok, status, message, data
        """
        status = response.status_code
        # 501 is a valid response (citizen already exists), not an error
        ok = 200 <= status < 300 or status == 501
        
        # Try to parse as JSON
        data = None
        try:
            data = response.json()
            # If JSON, extract message if available
            if isinstance(data, dict) and "message" in data:
                message = data["message"]
            else:
                message = response.text
        except Exception:
            # Not JSON, use text
            message = response.text
        
        # Handle specific status codes
        if status == 204:
            message = "Sin contenido" if not message else message
        elif status == 501:
            message = f"Error de parámetros o estado: {message}"
        
        return MinTICResponse(
            ok=ok,
            status=status,
            message=message,
            data=data
        )
    
    @staticmethod
    def _should_retry(result: Optional[MinTICResponse]) -> bool:
        """Determine if request should be retried.
        
        Retry only on:
        - 5xx errors (except 501 = parameter/state error)
        - Timeouts
        
        Do NOT retry on:
        - 2xx (success)
        - 4xx (client errors)
        - 501 (parameter/state error - won't change with retry)
        
        Args:
            result: MinTICResponse or None (None means exception)
            
        Returns:
            True if should retry
        """
        if result is None:
            # Exception occurred (timeout, connection error)
            return True
        
        if result.status == 501:
            # Parameter/state error - don't retry
            return False
        
        if 500 <= result.status < 600:
            # Other 5xx errors - retry
            return True
        
        # Don't retry 2xx, 3xx, 4xx
        return False
    
    async def _check_idempotency(self, key: str) -> Optional[MinTICResponse]:
        """Check if operation was already executed (idempotency).
        
        Args:
            key: Idempotency key (e.g., hub:registerCitizen:123)
            
        Returns:
            Cached response if exists and was successful, None otherwise
        """
        try:
            from carpeta_common.redis_client import get_json
            
            cached = await get_json(key)
            if cached:
                # Check if previous call was terminal (2xx, 204, 501)
                status = cached.get('status', 0)
                
                if 200 <= status < 300 or status in [204, 501]:
                    logger.info(
                        f"🔁 Idempotency: Operation already executed with status {status}, "
                        f"returning cached result"
                    )
                    return MinTICResponse(**cached)
            
            return None
            
        except ImportError:
            logger.debug("carpeta_common not available, idempotency disabled")
            return None
        except Exception as e:
            logger.warning(f"⚠️  Idempotency check failed: {e}")
            return None
    
    async def _save_idempotent_result(self, key: str, result: MinTICResponse, ttl: int = 900):
        """Save operation result for idempotency.
        
        Args:
            key: Idempotency key
            result: Operation result
            ttl: Time to live in seconds (default 900s = 15min)
        """
        try:
            from carpeta_common.redis_client import set_json
            
            # Only cache terminal statuses (2xx, 204, 501)
            if result.ok or result.status in [204, 501]:
                await set_json(key, result.model_dump(), ttl=ttl)
                logger.debug(f"💾 Saved idempotent result: {key} (TTL={ttl}s)")
        except ImportError:
            pass  # Idempotency disabled without Redis
        except Exception as e:
            logger.warning(f"⚠️  Failed to save idempotent result: {e}")
    
    async def _enqueue_for_retry(self, operation: str, payload: dict):
        """Enqueue operation for later retry when circuit breaker is OPEN.
        
        Args:
            operation: Operation name
            payload: Request payload
        """
        try:
            from carpeta_common.message_broker import publish_event
            from datetime import datetime
            
            await publish_event(
                event_type=f"hub.{operation}.queued",
                queue_name="hub-retry-queue",
                payload={
                    "operation": operation,
                    "data": payload,
                    "queued_at": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"📨 Operation queued for retry: {operation}")
        except ImportError:
            logger.warning("⚠️  Message broker not available, cannot queue operation")
        except Exception as e:
            logger.error(f"❌ Failed to queue operation: {e}")
    
    def _record_metrics(self, endpoint: str, duration: float, status: int, success: bool):
        """Record metrics for hub call.
        
        Args:
            endpoint: Hub endpoint name
            duration: Call duration in seconds
            status: HTTP status code
            success: Whether call succeeded
        """
        if OTEL_AVAILABLE and hasattr(self, 'hub_calls'):
            attributes = {
                "endpoint": endpoint,
                "status": status,
                "success": success
            }
            
            self.hub_calls.add(1, attributes)
            self.hub_latency.record(duration, attributes)
            
            # Success rate
            if hasattr(self, 'hub_success_rate'):
                self.hub_success_rate.add(1 if success else 0, {"endpoint": endpoint})
            
            # Status code breakdown
            if hasattr(self, 'hub_status_codes'):
                self.hub_status_codes.add(1, {
                    "endpoint": endpoint,
                    "status_code": str(status),
                    "status_class": f"{status//100}xx" if status > 0 else "timeout"
                })

    @retry(
        retry=retry_if_result(_should_retry.__func__) | retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10) + wait_random(0, 2),
        reraise=True
    )
    async def register_citizen(self, request: RegisterCitizenRequest) -> MinTICResponse:
        """Register citizen in MinTIC Hub with full functionality.

        POST /apis/registerCitizen
        Responses:
        - 201: Ciudadano registrado exitosamente
        - 501: Error - ciudadano ya existe
        - 500: Application Error
        """
        endpoint_name = "registerCitizen"
        
        # Check hub rate limit
        allowed, remaining = await self.hub_rate_limiter.check_limit(endpoint_name)
        if not allowed:
            logger.warning(f"⚠️  Hub rate limit EXCEEDED for {endpoint_name}")
            return MinTICResponse(
                ok=True,
                status=202,
                message=f"Hub rate limit exceeded ({self.settings.hub_rate_limit_per_minute} req/min), operation queued for retry",
                data={"queued": True, "reason": "rate_limit", "remaining": remaining}
            )
        
        # Check idempotency
        idempotency_key = f"hub:registerCitizen:{request.id}"
        cached = await self._check_idempotency(idempotency_key)
        if cached:
            return cached
        
        # Check circuit breaker
        cb = self.circuit_breakers.get(endpoint_name)
        if cb and cb.state == CircuitBreakerState.OPEN:
            logger.warning(f"⚠️  Circuit breaker OPEN for {endpoint_name}")
            return MinTICResponse(
                ok=True,
                status=202,
                message="Circuit breaker OPEN, operation queued for retry",
                data={"queued": True, "reason": "circuit_breaker"}
            )
        
        try:
            logger.info(f"📤 Calling hub registerCitizen: id={request.id}, operator={request.operatorId}")
            
            # Execute with circuit breaker
            async def _call():
                response = await self.client.post(
                    "/apis/registerCitizen",
                    json=request.model_dump(),
                )
                
                # Only treat 5xx as errors, not 4xx or specific codes like 501
                if 500 <= response.status_code < 600 and response.status_code != 501:
                    raise httpx.HTTPStatusError(
                        f"Hub returned {response.status_code}",
                        request=response.request,
                        response=response
                    )
                
                return response
            
            # Call with circuit breaker
            if cb:
                response = await cb.call(_call)
            else:
                response = await _call()
            
            result = self._parse_response(response)
            
            if result.status == 201:
                logger.info(f"✅ Citizen {request.id} registered in hub")
            elif result.status == 501:
                logger.warning(f"⚠️  Citizen {request.id} already exists: {result.message}")
            else:
                logger.error(f"❌ Hub error: {result.status} - {result.message}")
            
            # Save for idempotency (TTL: 15 minutes)
            await self._save_idempotent_result(idempotency_key, result, ttl=900)
            
            return result
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.error(f"❌ Hub communication error: {e}")
            raise  # Let retry decorator handle it

    @retry(
        retry=retry_if_result(_should_retry.__func__) | retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10) + wait_random(0, 2),
        reraise=True
    )
    async def unregister_citizen(
        self, request: UnregisterCitizenRequest
    ) -> MinTICResponse:
        """Unregister citizen from MinTIC Hub with idempotency.

        DELETE /apis/unregisterCitizen
        Responses:
        - 201: Deleted
        - 204: No Content (sin contenido)
        - 501: Error (no retry)
        - 500: Application Error (retry)
        """
        endpoint_name = "unregisterCitizen"
        
        # Check hub rate limit
        allowed, remaining = await self.hub_rate_limiter.check_limit(endpoint_name)
        if not allowed:
            logger.warning(f"⚠️  Hub rate limit EXCEEDED for {endpoint_name}")
            await self._enqueue_for_retry(endpoint_name, request.model_dump())
            return MinTICResponse(
                ok=True,
                status=202,
                message="Hub rate limit exceeded, operation queued",
                data={"queued": True, "reason": "rate_limit"}
            )
        
        # Check idempotency
        idempotency_key = f"hub:unregisterCitizen:{request.id}"
        cached = await self._check_idempotency(idempotency_key)
        if cached:
            return cached
        
        try:
            response = await self.client.request(
                "DELETE",
                "/apis/unregisterCitizen",
                json=request.model_dump(),
            )
            
            result = self._parse_response(response)
            
            if result.ok:
                logger.info(f"✅ Citizen {request.id} unregistered from hub")
            else:
                logger.warning(f"⚠️  Unregister failed: {result.status} - {result.message}")
            
            # Save for idempotency (TTL: 5 minutes)
            await self._save_idempotent_result(idempotency_key, result, ttl=300)
            
            return result
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.error(f"❌ Hub communication error: {e}")
            raise  # Let retry decorator handle it

    @retry(
        retry=retry_if_result(_should_retry.__func__) | retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10) + wait_random(0, 2),
        reraise=True
    )
    async def authenticate_document(
        self, request: AuthenticateDocumentRequest
    ) -> MinTICResponse:
        """Authenticate document in MinTIC Hub with idempotency.

        PUT /apis/authenticateDocument
        Responses:
        - 200: Documento autenticado exitosamente
        - 204: No Content (sin contenido)
        - 501: Error de parámetros (no retry)
        - 500: Application Error (retry)
        """
        # Check idempotency (use document URL hash for key)
        # Note: We could use document_id, but using citizen_id for grouping
        import hashlib
        url_hash = hashlib.sha256(request.UrlDocument.encode()).hexdigest()[:16]
        idempotency_key = f"hub:authdoc:{request.idCitizen}:{url_hash}"
        
        cached = await self._check_idempotency(idempotency_key)
        if cached:
            return cached
        
        try:
            # Sanitize data (minimal: only citizen_id, URL, title)
            sanitized_data = DataSanitizer.sanitize_authenticate_document(request.model_dump())
            
            # Masked log (don't expose full citizen ID or URL in logs)
            masked_id = DataSanitizer.mask_pii(str(request.idCitizen), show_chars=4)
            masked_url = DataSanitizer.mask_pii(request.UrlDocument, show_chars=20)
            logger.info(
                f"📤 Calling hub authenticateDocument: "
                f"citizen={masked_id}, url={masked_url}, title={request.documentTitle}"
            )
            
            response = await self.client.put(
                "/apis/authenticateDocument",
                json=sanitized_data,  # Send only required fields
            )
            
            result = self._parse_response(response)
            
            # Audit log
            await AuditLogger.log_hub_call(
                operation="authenticateDocument",
                sanitized_payload=sanitized_data,
                response_status=result.status,
                response_message=result.message
            )
            
            if result.ok:
                logger.info(f"✅ Document authenticated for citizen {masked_id}")
            else:
                logger.warning(f"⚠️  Authentication failed: {result.status} - {result.message}")
            
            # Save for idempotency (TTL: 15 minutes)
            await self._save_idempotent_result(idempotency_key, result, ttl=900)
            
            return result
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.error(f"❌ Hub communication error: {e}")
            raise  # Let retry decorator handle it

    @retry(
        retry=retry_if_result(_should_retry.__func__) | retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10) + wait_random(0, 2),
        reraise=True
    )
    async def validate_citizen(self, citizen_id: int) -> MinTICResponse:
        """Validate citizen in MinTIC Hub.

        GET /apis/validateCitizen/{id}
        Responses:
        - 200: Citizen exists and is valid
        - 204: Citizen not found (sin contenido)
        - 501: Invalid ID format (no retry)
        - 500: Application Error (retry)
        """
        try:
            response = await self.client.get(f"/apis/validateCitizen/{citizen_id}")
            
            result = self._parse_response(response)
            
            if result.status == 200:
                logger.info(f"✅ Citizen {citizen_id} validated")
            elif result.status == 204:
                logger.info(f"ℹ️  Citizen {citizen_id} not found (204 No Content)")
            else:
                logger.warning(f"⚠️  Validation failed: {result.status} - {result.message}")
            
            return result
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.error(f"❌ Hub communication error: {e}")
            raise  # Let retry decorator handle it

    @retry(
        retry=retry_if_result(_should_retry.__func__) | retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10) + wait_random(0, 2),
        reraise=True
    )
    async def register_operator(self, request: RegisterOperatorRequest) -> MinTICResponse:
        """Register operator in MinTIC Hub.

        POST /apis/registerOperator
        Responses:
        - 201: Operator registered, returns ID
        - 501: Operator already exists (no retry)
        - 500: Application Error (retry)
        """
        try:
            response = await self.client.post(
                "/apis/registerOperator",
                json=request.model_dump(),
            )
            
            result = self._parse_response(response)
            
            if result.ok:
                logger.info(f"✅ Operator '{request.name}' registered in hub")
            else:
                logger.warning(f"⚠️  Operator registration failed: {result.status} - {result.message}")
            
            return result
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.error(f"❌ Hub communication error: {e}")
            raise  # Let retry decorator handle it

    @retry(
        retry=retry_if_result(_should_retry.__func__) | retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10) + wait_random(0, 2),
        reraise=True
    )
    async def register_transfer_endpoint(
        self, request: RegisterTransferEndPointRequest
    ) -> MinTICResponse:
        """Register transfer endpoint in MinTIC Hub.

        PUT /apis/registerTransferEndPoint
        Responses:
        - 201: Endpoint registered
        - 501: Invalid endpoint or operator (no retry)
        - 500: Application Error (retry)
        """
        try:
            response = await self.client.put(
                "/apis/registerTransferEndPoint",
                json=request.model_dump(),
            )
            
            result = self._parse_response(response)
            
            if result.ok:
                logger.info(f"✅ Transfer endpoint registered for operator {request.idOperator}")
            else:
                logger.warning(f"⚠️  Endpoint registration failed: {result.status} - {result.message}")
            
            return result
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.error(f"❌ Hub communication error: {e}")
            raise  # Let retry decorator handle it

    def _normalize_operator(self, raw_data: dict) -> Optional[OperatorInfo]:
        """Normalize and validate operator data.
        
        Tolerates:
        - Missing fields
        - Extra whitespace
        - Inconsistent casing
        - Missing transferAPIURL
        
        Args:
            raw_data: Raw operator data from hub
            
        Returns:
            OperatorInfo or None if invalid/filtered
        """
        try:
            # Normalize field names (case-insensitive)
            normalized = {}
            for key, value in raw_data.items():
                key_lower = key.lower()
                
                # Map common variations
                if key_lower in ('operatorid', 'operator_id', 'id'):
                    normalized['OperatorId'] = str(value).strip() if value else ""
                elif key_lower in ('operatorname', 'operator_name', 'name'):
                    normalized['OperatorName'] = str(value).strip() if value else ""
                elif key_lower in ('transferapiurl', 'transfer_api_url', 'transferurl', 'url'):
                    url = str(value).strip() if value else ""
                    normalized['transferAPIURL'] = url
            
            # Check required fields
            if not normalized.get('OperatorId'):
                logger.warning(f"⚠️  Operator missing OperatorId, skipping: {raw_data}")
                return None
            
            if not normalized.get('OperatorName'):
                logger.warning(f"⚠️  Operator missing OperatorName, skipping: {raw_data}")
                return None
            
            # Filter out operators without transfer URL
            if not normalized.get('transferAPIURL'):
                logger.info(f"ℹ️  Operator {normalized['OperatorId']} has no transferAPIURL, filtering out")
                return None
            
            # Validate URL security (https:// required in production)
            transfer_url = normalized['transferAPIURL']
            
            if transfer_url.startswith('http://'):
                if self.settings.environment == "production" and not self.settings.allow_insecure_operator_urls:
                    logger.error(
                        f"🚫 Operator {normalized['OperatorId']} has insecure URL (http://) "
                        f"- rejecting in production: {transfer_url}"
                    )
                    return None
                else:
                    logger.warning(
                        f"⚠️  Operator {normalized['OperatorId']} using insecure URL (http://): {transfer_url} "
                        f"- allowed in {self.settings.environment} environment"
                    )
            
            # Create OperatorInfo
            return OperatorInfo(**normalized)
            
        except Exception as e:
            logger.error(f"❌ Error normalizing operator: {e} - Data: {raw_data}")
            return None
    
    async def get_operators(self) -> tuple[list[OperatorInfo], MinTICResponse]:
        """Get all operators from MinTIC Hub with Redis cache and anti-stampede.
        
        GET /apis/getOperators
        
        Features:
        - Redis cache (300s TTL)
        - Anti-stampede pattern (single-flight with locks)
        - Normalizes operator data (tolerates missing fields)
        - Filters operators without transferAPIURL
        - Validates https:// in production
        
        Responses:
        - 200: List of operators (JSON array)
        - 204: No operators (sin contenido)
        - 500: Application Error (retry)
        """
        cache_key = "mintic:operators"
        lock_key = "lock:mintic:operators"
        
        # Try cache first
        try:
            from carpeta_common.redis_client import get_json, set_json, acquire_lock, release_lock
            
            # Check cache
            cached = await get_json(cache_key)
            if cached:
                logger.info(f"📦 Cache HIT: {cache_key} ({len(cached)} operators)")
                
                # Parse from cache
                operators = [OperatorInfo(**op) for op in cached]
                
                return operators, MinTICResponse(
                    ok=True,
                    status=200,
                    message=f"Retrieved from cache ({len(operators)} operators)",
                    data=cached
                )
        except ImportError:
            logger.warning("⚠️  carpeta_common not available, cache disabled")
        except Exception as e:
            logger.warning(f"⚠️  Cache read failed: {e}")
        
        # Cache miss or error - fetch from hub with anti-stampede lock
        lock_token = None
        
        try:
            from carpeta_common.redis_client import acquire_lock, release_lock
            
            # Try to acquire lock (only one pod fetches)
            lock_token = await acquire_lock(lock_key, ttl=10)
            
            if not lock_token:
                # Another pod is fetching, wait and retry cache
                logger.info("🔒 Another pod is fetching operators, waiting...")
                await asyncio.sleep(1)
                
                # Check cache again
                try:
                    cached = await get_json(cache_key)
                    if cached:
                        logger.info(f"📦 Cache populated by other pod ({len(cached)} operators)")
                        operators = [OperatorInfo(**op) for op in cached]
                        return operators, MinTICResponse(
                            ok=True,
                            status=200,
                            message="Retrieved from cache (waited for other pod)",
                            data=cached
                        )
                except Exception:
                    pass
                
                # If still no cache, fetch ourselves
                logger.info("⚠️  Cache still empty, fetching anyway")
        
        except ImportError:
            pass  # No anti-stampede without Redis
        except Exception as e:
            logger.warning(f"⚠️  Lock acquisition failed: {e}")
        
        # Fetch from hub
        try:
            response = await self.client.get("/apis/getOperators")
            
            result = self._parse_response(response)
            
            if result.ok and result.data and isinstance(result.data, list):
                # Normalize and filter operators
                normalized_operators = []
                
                for raw_op in result.data:
                    normalized = self._normalize_operator(raw_op)
                    if normalized:
                        normalized_operators.append(normalized)
                    # else: filtered out (logged in _normalize_operator)
                
                logger.info(
                    f"✅ Retrieved {len(result.data)} operators from hub, "
                    f"{len(normalized_operators)} valid after filtering"
                )
                
                # Cache valid operators
                try:
                    from carpeta_common.redis_client import set_json
                    
                    cache_data = [op.model_dump() for op in normalized_operators]
                    await set_json(cache_key, cache_data, ttl=300)
                    logger.info(f"💾 Cached {len(normalized_operators)} operators (TTL=300s)")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to cache operators: {e}")
                
                return normalized_operators, result
                
            elif result.status == 204:
                # No operators
                logger.info("ℹ️  No operators found (204 No Content)")
                return [], result
            else:
                logger.warning(f"⚠️  Get operators failed: {result.status} - {result.message}")
                return [], result
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.error(f"❌ Hub communication error: {e}")
            raise  # Let retry decorator handle it (handled by outer retry decorator)
        
        finally:
            # Release lock if acquired
            if lock_token:
                try:
                    from carpeta_common.redis_client import release_lock
                    await release_lock(lock_key, lock_token)
                except Exception as e:
                    logger.warning(f"⚠️  Lock release failed: {e}")

    # New methods for enhanced MinTIC Hub integration

    async def sync_citizen_documents(
        self,
        citizen_id: str,
        document_ids: list[str] = None,
        sync_type: str = "full"
    ) -> dict:
        """Sync citizen documents with MinTIC Hub."""
        logger.info(f"Syncing documents for citizen {citizen_id} (type: {sync_type})")
        
        try:
            # Get citizen documents from local system
            # Document service call
            local_documents = await self._get_local_citizen_documents(citizen_id)
            
            if not local_documents:
                return {
                    "synced_count": 0,
                    "failed_count": 0,
                    "timestamp": self.get_current_timestamp(),
                    "details": ["No documents found for citizen"]
                }
            
            # Filter by specific document IDs if provided
            if document_ids:
                local_documents = [doc for doc in local_documents if doc.get('id') in document_ids]
            
            synced_count = 0
            failed_count = 0
            details = []
            
            # Sync each document with hub
            for document in local_documents:
                try:
                    # Authenticate document with hub
                    auth_request = AuthenticateDocumentRequest(
                        idCitizen=int(citizen_id),
                        UrlDocument=document.get('download_url', ''),
                        documentTitle=document.get('title', 'Documento')
                    )
                    
                    result = await self.authenticate_document(auth_request)
                    
                    if result.success:
                        synced_count += 1
                        details.append(f"Document {document.get('id')} synced successfully")
                        
                        # Update document status in local system
                        await self._update_document_status(
                            document.get('id'), 
                            'synced', 
                            {'hub_response': result.data}
                        )
                    else:
                        failed_count += 1
                        details.append(f"Document {document.get('id')} sync failed: {result.message}")
                        
                except Exception as e:
                    failed_count += 1
                    details.append(f"Document {document.get('id')} sync error: {str(e)}")
                    logger.error(f"Document sync error: {e}")
            
            # Update sync status in cache
            cache_key = f"sync_status:{citizen_id}"
            sync_status = {
                "last_sync": self.get_current_timestamp(),
                "status": "completed" if failed_count == 0 else "partial",
                "documents_synced": synced_count,
                "pending_sync": failed_count,
                "last_error": None if failed_count == 0 else f"{failed_count} documents failed",
                "next_sync": self.get_current_timestamp()
            }
            await self.redis_client.setex(cache_key, 300, sync_status)
            
            return {
                "synced_count": synced_count,
                "failed_count": failed_count,
                "timestamp": self.get_current_timestamp(),
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Document sync failed: {e}")
            raise

    async def handle_document_authentication(self, payload: dict) -> None:
        """Handle document authentication notification from hub."""
        logger.info("Processing document authentication notification")
        
        try:
            document_id = payload.get('document_id')
            citizen_id = payload.get('citizen_id')
            authentication_result = payload.get('authentication_result')
            
            # Local document status update
            
            logger.info(f"Document {document_id} authenticated for citizen {citizen_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle document authentication: {e}")

    async def handle_citizen_update(self, payload: dict) -> None:
        """Handle citizen update notification from hub."""
        logger.info("Processing citizen update notification")
        
        try:
            citizen_id = payload.get('citizen_id')
            update_type = payload.get('update_type')
            
            # Local citizen data update
            
            logger.info(f"Citizen {citizen_id} updated: {update_type}")
            
        except Exception as e:
            logger.error(f"Failed to handle citizen update: {e}")

    async def handle_operator_status_change(self, payload: dict) -> None:
        """Handle operator status change notification from hub."""
        logger.info("Processing operator status change notification")
        
        try:
            operator_id = payload.get('operator_id')
            new_status = payload.get('status')
            
            # Operator status cache update
            
            logger.info(f"Operator {operator_id} status changed to: {new_status}")
            
        except Exception as e:
            logger.error(f"Failed to handle operator status change: {e}")

    async def handle_transfer_completion(self, payload: dict) -> None:
        """Handle transfer completion notification from hub."""
        logger.info("Processing transfer completion notification")
        
        try:
            transfer_id = payload.get('transfer_id')
            status = payload.get('status')
            result = payload.get('result')
            
            # Local transfer status update
            
            logger.info(f"Transfer {transfer_id} completed with status: {status}")
            
        except Exception as e:
            logger.error(f"Failed to handle transfer completion: {e}")

    async def get_citizen_sync_status(self, citizen_id: str) -> dict:
        """Get synchronization status for a citizen."""
        logger.info(f"Getting sync status for citizen: {citizen_id}")
        
        try:
            # Try to get from Redis cache first
            cache_key = f"sync_status:{citizen_id}"
            cached_status = await self.redis_client.get(cache_key)
            
            if cached_status:
                logger.info(f"Found cached sync status for citizen {citizen_id}")
                return cached_status
            
            # If not in cache, get from database
            # Call metadata service to get sync status
            metadata_url = f"{self.settings.metadata_url}/api/sync/status/{citizen_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(metadata_url)
                response.raise_for_status()
                
                sync_status = response.json()
                
                # Cache the result for 5 minutes
                await self.redis_client.setex(cache_key, 300, sync_status)
                
                return sync_status
                
        except Exception as e:
            logger.error(f"Failed to get sync status for citizen {citizen_id}: {e}")
            return {
                "last_sync": None,
                "status": "error",
                "documents_synced": 0,
                "pending_sync": 0,
                "last_error": str(e),
                "next_sync": None
            }

    async def validate_document_with_hub(
        self,
        document_id: str,
        document_hash: str,
        citizen_id: str
    ) -> dict:
        """Validate document with MinTIC Hub using authenticateDocument endpoint.
        
        According to the documentation:
        1. Perform local validation (hash, signature verification)
        2. Get real document URL from document service
        3. Notify hub that document was authenticated
        """
        logger.info(f"Validating document {document_id} with MinTIC Hub")
        
        try:
            # Step 1: Perform local validation (hash, signature, etc.)
            local_validation_result = await self._perform_local_document_validation(
                document_id, document_hash, citizen_id
            )
            
            if not local_validation_result["is_valid"]:
                return {
                    "is_valid": False,
                    "timestamp": self.get_current_timestamp(),
                    "hub_response": {"error": "Local validation failed"},
                    "details": {
                        "document_id": document_id,
                        "citizen_id": citizen_id,
                        "validation_status": "local_validation_failed",
                        "local_errors": local_validation_result.get("errors", [])
                    }
                }
            
            # Step 2: Get the real document URL (SAS URL from Azure Blob Storage)
            document_url = await self._get_document_sas_url(document_id)
            
            # Step 3: Create authentication request for MinTIC Hub
            auth_request = AuthenticateDocumentRequest(
                idCitizen=int(citizen_id),
                UrlDocument=document_url,  # Real SAS URL from Azure Blob Storage
                documentTitle=f"Documento {document_id}"
            )
            
            # Step 4: Call MinTIC Hub to authenticate the document
            result = await self.authenticate_document(auth_request)
            
            return {
                "is_valid": result.success,
                "timestamp": self.get_current_timestamp(),
                "hub_response": {
                    "status_code": result.status_code,
                    "message": result.message,
                    "data": result.data
                },
                "details": {
                    "document_id": document_id,
                    "citizen_id": citizen_id,
                    "validation_status": "hub_authenticated" if result.success else "hub_authentication_failed",
                    "document_url": document_url,
                    "local_validation": local_validation_result
                }
            }
            
        except Exception as e:
            logger.error(f"Document authentication with hub failed: {e}")
            return {
                "is_valid": False,
                "timestamp": self.get_current_timestamp(),
                "hub_response": {"error": str(e)},
                "details": {
                    "document_id": document_id,
                    "citizen_id": citizen_id,
                    "validation_status": "error"
                }
            }

    async def _get_local_citizen_documents(self, citizen_id: str) -> list[dict]:
        """Get citizen documents from local system."""
        try:
            # Call metadata service to get citizen documents
            metadata_url = f"{self.settings.metadata_url}/api/documents/citizen/{citizen_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(metadata_url)
                response.raise_for_status()
                
                documents_data = response.json()
                
                # Transform to expected format
                documents = []
                for doc in documents_data.get('documents', []):
                    documents.append({
                        "id": doc.get('id'),
                        "title": doc.get('title', 'Documento'),
                        "sha256_hash": doc.get('sha256_hash'),
                        "size": doc.get('size', 0),
                        "uploaded_at": doc.get('created_at'),
                        "status": doc.get('status', 'pending')
                    })
                
                return documents
                
        except Exception as e:
            logger.error(f"Failed to get local documents for citizen {citizen_id}: {e}")
            # Return empty list on error
            return []


    async def handle_document_authentication(self, payload: dict) -> None:
        """Handle document authentication notification from hub."""
        try:
            document_id = payload.get('document_id')
            citizen_id = payload.get('citizen_id')
            authentication_result = payload.get('authentication_result')
            
            logger.info(f"Document {document_id} authenticated for citizen {citizen_id}")
            
            # Update local document status
            await self._update_document_status(document_id, 'authenticated', authentication_result)
            
        except Exception as e:
            logger.error(f"Failed to handle document authentication: {e}")

    async def handle_citizen_update(self, payload: dict) -> None:
        """Handle citizen update notification from hub."""
        try:
            citizen_id = payload.get('citizen_id')
            update_type = payload.get('update_type')
            
            logger.info(f"Citizen {citizen_id} updated: {update_type}")
            
            # Update local citizen data
            await self._update_citizen_data(citizen_id, update_type, payload)
            
        except Exception as e:
            logger.error(f"Failed to handle citizen update: {e}")

    async def handle_operator_status_change(self, payload: dict) -> None:
        """Handle operator status change notification from hub."""
        try:
            operator_id = payload.get('operator_id')
            new_status = payload.get('status')
            
            logger.info(f"Operator {operator_id} status changed to: {new_status}")
            
            # Update operator status cache
            await self._update_operator_status(operator_id, new_status)
            
        except Exception as e:
            logger.error(f"Failed to handle operator status change: {e}")

    async def handle_transfer_completion(self, payload: dict) -> None:
        """Handle transfer completion notification from hub."""
        try:
            transfer_id = payload.get('transfer_id')
            status = payload.get('status')
            result = payload.get('result')
            
            logger.info(f"Transfer {transfer_id} completed with status: {status}")
            
            # Update local transfer status
            await self._update_transfer_status(transfer_id, status, result)
            
        except Exception as e:
            logger.error(f"Failed to handle transfer completion: {e}")

    async def _update_document_status(self, document_id: str, status: str, result: dict) -> None:
        """Update document status in local system."""
        try:
            # Call metadata service to update document status
            metadata_url = f"{self.settings.metadata_url}/api/documents/{document_id}/status"
            
            update_data = {
                "status": status,
                "authentication_result": result,
                "updated_at": self.get_current_timestamp()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(metadata_url, json=update_data)
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to update document status: {e}")

    async def _update_citizen_data(self, citizen_id: str, update_type: str, data: dict) -> None:
        """Update citizen data in local system."""
        try:
            # Call citizen service to update citizen data
            citizen_url = f"{self.settings.citizen_url}/api/citizens/{citizen_id}"
            
            update_data = {
                "update_type": update_type,
                "data": data,
                "updated_at": self.get_current_timestamp()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(citizen_url, json=update_data)
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to update citizen data: {e}")

    async def _update_operator_status(self, operator_id: str, status: str) -> None:
        """Update operator status in local cache."""
        try:
            # Update operator status in Redis cache
            cache_key = f"operator:{operator_id}:status"
            cache_data = {
                "status": status,
                "updated_at": self.get_current_timestamp()
            }
            
            # Store in Redis cache
            await self._cache_operator_status(cache_key, cache_data)
            
        except Exception as e:
            logger.error(f"Failed to update operator status: {e}")

    async def _update_transfer_status(self, transfer_id: str, status: str, result: dict) -> None:
        """Update transfer status in local system."""
        try:
            # Call transfer service to update transfer status
            transfer_url = f"{self.settings.transfer_url}/api/transfers/{transfer_id}/status"
            
            update_data = {
                "status": status,
                "result": result,
                "updated_at": self.get_current_timestamp()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(transfer_url, json=update_data)
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to update transfer status: {e}")

    async def _cache_operator_status(self, cache_key: str, data: dict) -> None:
        """Cache operator status in Redis."""
        try:
            # Use Redis client to cache data
            if self.redis_client:
                await self.redis_client.setex(cache_key, 3600, data)  # 1 hour TTL
        except Exception as e:
            logger.error(f"Failed to cache operator status: {e}")

    
    async def _perform_local_document_validation(
        self, document_id: str, document_hash: str, citizen_id: str
    ) -> dict:
        """Perform local document validation (hash, signature, etc.)."""
        try:
            # Call local signature service to validate document
            signature_url = f"{self.settings.signature_url}/api/documents/{document_id}/validate"
            
            validation_data = {
                "document_id": document_id,
                "document_hash": document_hash,
                "citizen_id": citizen_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(signature_url, json=validation_data)
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "is_valid": result.get("is_valid", False),
                        "validation_type": "local_signature_validation",
                        "errors": result.get("errors", [])
                    }
                else:
                    return {
                        "is_valid": False,
                        "validation_type": "local_signature_validation",
                        "errors": [f"Signature service error: {response.status_code}"]
                    }
                    
        except Exception as e:
            logger.error(f"Local document validation failed: {e}")
            return {
                "is_valid": False,
                "validation_type": "local_signature_validation",
                "errors": [str(e)]
            }

    async def _get_document_sas_url(self, document_id: str) -> str:
        """Get SAS URL for document from Azure Blob Storage."""
        try:
            # Call document service to get SAS URL
            document_url = f"{self.settings.document_url}/api/documents/{document_id}/sas-url"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(document_url)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("sas_url")
                else:
                    logger.error(f"Failed to get SAS URL from document service: {response.status_code}")
                    raise Exception(f"Document service error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to get document SAS URL: {e}")
            raise Exception(f"Cannot get document URL: {str(e)}")

    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

