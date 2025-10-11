"""MinTIC Hub HTTP client with mTLS and retry logic."""

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
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

logger = logging.getLogger(__name__)


class MinTICClient:
    """HTTP client for MinTIC Hub with mTLS support."""

    def __init__(self, settings: Settings) -> None:
        """Initialize MinTIC client."""
        self.settings = settings
        self.base_url = settings.mintic_base_url

        # Configure mTLS
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            cert=(settings.mtls_cert_path, settings.mtls_key_path),
            verify=settings.ca_bundle_path,
            timeout=settings.request_timeout,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def register_citizen(self, request: RegisterCitizenRequest) -> MinTICResponse:
        """Register citizen in MinTIC Hub.

        POST /apis/registerCitizen
        Responses:
        - 201: Ciudadano con id: 123 se ha relacionado con OPerador abc. Creado exitosamente
        - 500: Application Error
        - 501: Error al crear Ciudadano con id: 123 ya se encuentra registrado
        """
        try:
            response = await self.client.post(
                "/apis/registerCitizen",
                json=request.model_dump(),
            )

            if response.status_code == 201:
                return MinTICResponse(
                    status_code=201, message=response.text, success=True
                )
            elif response.status_code in (500, 501):
                return MinTICResponse(
                    status_code=response.status_code,
                    message=response.text,
                    success=False,
                )
            else:
                return MinTICResponse(
                    status_code=response.status_code,
                    message=f"Unexpected response: {response.text}",
                    success=False,
                )
        except httpx.HTTPError as e:
            logger.error(f"Error registering citizen: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def unregister_citizen(
        self, request: UnregisterCitizenRequest
    ) -> MinTICResponse:
        """Unregister citizen from MinTIC Hub.

        DELETE /apis/unregisterCitizen
        Responses:
        - 201: Deleted
        - 204: No Content
        - 500: Application Error
        - 501: Error
        """
        try:
            response = await self.client.request(
                "DELETE",
                "/apis/unregisterCitizen",
                json=request.model_dump(),
            )

            if response.status_code in (201, 204):
                return MinTICResponse(
                    status_code=response.status_code,
                    message="Citizen unregistered successfully",
                    success=True,
                )
            else:
                return MinTICResponse(
                    status_code=response.status_code,
                    message=response.text,
                    success=False,
                )
        except httpx.HTTPError as e:
            logger.error(f"Error unregistering citizen: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def authenticate_document(
        self, request: AuthenticateDocumentRequest
    ) -> MinTICResponse:
        """Authenticate document in MinTIC Hub.

        PUT /apis/authenticateDocument
        Responses:
        - 200: El documento: Diploma Grado del ciudadano 1234567890 ha sido autenticado exitosamente
        - 204: No Content
        - 500: Application Error
        - 501: Error
        """
        try:
            response = await self.client.put(
                "/apis/authenticateDocument",
                json=request.model_dump(),
            )

            if response.status_code == 200:
                return MinTICResponse(
                    status_code=200, message=response.text, success=True
                )
            elif response.status_code == 204:
                return MinTICResponse(
                    status_code=204, message="No content", success=True
                )
            else:
                return MinTICResponse(
                    status_code=response.status_code,
                    message=response.text,
                    success=False,
                )
        except httpx.HTTPError as e:
            logger.error(f"Error authenticating document: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def validate_citizen(self, citizen_id: int) -> MinTICResponse:
        """Validate citizen in MinTIC Hub.

        GET /apis/validateCitizen/{id}
        Responses:
        - 200: OK
        - 204: No Content
        - 500: Application Error
        - 501: Error
        """
        try:
            response = await self.client.get(f"/apis/validateCitizen/{citizen_id}")

            if response.status_code == 200:
                return MinTICResponse(
                    status_code=200, message="Citizen validated", success=True
                )
            elif response.status_code == 204:
                return MinTICResponse(
                    status_code=204, message="Citizen not found", success=False
                )
            else:
                return MinTICResponse(
                    status_code=response.status_code,
                    message=response.text,
                    success=False,
                )
        except httpx.HTTPError as e:
            logger.error(f"Error validating citizen: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def register_operator(self, request: RegisterOperatorRequest) -> MinTICResponse:
        """Register operator in MinTIC Hub.

        POST /apis/registerOperator
        Responses:
        - 201: Returns operator ID (e.g., "65ca0a00d833e984e2608756")
        - 500: Application Error
        - 501: Error
        """
        try:
            response = await self.client.post(
                "/apis/registerOperator",
                json=request.model_dump(),
            )

            if response.status_code == 201:
                return MinTICResponse(
                    status_code=201, message=response.text, success=True
                )
            else:
                return MinTICResponse(
                    status_code=response.status_code,
                    message=response.text,
                    success=False,
                )
        except httpx.HTTPError as e:
            logger.error(f"Error registering operator: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def register_transfer_endpoint(
        self, request: RegisterTransferEndPointRequest
    ) -> MinTICResponse:
        """Register transfer endpoint in MinTIC Hub.

        PUT /apis/registerTransferEndPoint
        Responses:
        - 201: Updated
        - 500: Application Error
        - 501: Error
        """
        try:
            response = await self.client.put(
                "/apis/registerTransferEndPoint",
                json=request.model_dump(),
            )

            if response.status_code == 201:
                return MinTICResponse(
                    status_code=201, message="Endpoint registered", success=True
                )
            else:
                return MinTICResponse(
                    status_code=response.status_code,
                    message=response.text,
                    success=False,
                )
        except httpx.HTTPError as e:
            logger.error(f"Error registering transfer endpoint: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def get_operators(self) -> tuple[list[OperatorInfo], MinTICResponse]:
        """Get all operators from MinTIC Hub.

        GET /apis/getOperators
        Responses:
        - 200: List of operators
        - 500: Application Error
        - 501: Error
        """
        try:
            response = await self.client.get("/apis/getOperators")

            if response.status_code == 200:
                operators_data = response.json()
                operators = [OperatorInfo(**op) for op in operators_data]
                return operators, MinTICResponse(
                    status_code=200, message="Success", success=True
                )
            else:
                return [], MinTICResponse(
                    status_code=response.status_code,
                    message=response.text,
                    success=False,
                )
        except httpx.HTTPError as e:
            logger.error(f"Error getting operators: {e}")
            raise

