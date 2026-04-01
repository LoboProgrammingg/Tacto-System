"""
Tacto External API Client - Infrastructure Implementation.

Handles OAuth2 authentication and communication with Tacto's external API.
Auth is fully internal — no endpoint is exposed for token generation.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import structlog

from tacto.config import TactoAPISettings, get_settings
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.infrastructure.circuit_breaker import CircuitBreaker, CircuitOpenError


logger = structlog.get_logger()


@dataclass
class _TactoToken:
    """Internal OAuth2 access token with expiry tracking."""

    access_token: str
    token_type: str
    expires_in: int
    obtained_at: float

    @property
    def is_expired(self) -> bool:
        """True if token expires within the next 30 seconds."""
        return time.time() > (self.obtained_at + self.expires_in - 30)


class TactoClient:
    """
    Tacto External API client.

    Handles:
    - OAuth2 Client Credentials flow (token cached internally, auto-renewed)
    - RAG full data for restaurant AI context
    - Institutional data

    All credentials come from environment via TactoAPISettings.
    Auth is never exposed as an API endpoint — it happens transparently
    before every authenticated request.
    """

    def __init__(self, settings: Optional[TactoAPISettings] = None) -> None:
        self._settings = settings or get_settings().tacto
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[_TactoToken] = None
        self._circuit_breaker = CircuitBreaker(name="tacto_api")

    async def connect(self) -> Success[bool] | Failure[Exception]:
        """Initialize HTTP client."""
        try:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=self._settings.http_timeout,
            )
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def disconnect(self) -> Success[bool] | Failure[Exception]:
        """Close HTTP client."""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            return Ok(True)
        except Exception as e:
            return Err(e)

    def _ensure_client(self) -> None:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=self._settings.http_timeout,
            )

    # ------------------------------------------------------------------ #
    # Auth — internal, never exposed                                       #
    # ------------------------------------------------------------------ #

    async def _ensure_token(self) -> Success[str] | Failure[Exception]:
        """Return cached token or fetch a new one transparently."""
        if self._token and not self._token.is_expired:
            return Ok(self._token.access_token)
        return await self._fetch_token()

    async def _fetch_token(self) -> Success[str] | Failure[Exception]:
        """
        Fetch OAuth2 token using Client Credentials grant.

        POST {TACTO_AUTH_URL}
        Content-Type: application/x-www-form-urlencoded
        Body: grant_type, client_id, client_secret [, scope]

        Includes retry (2 attempts, 2s delay) for transient network failures.
        """
        if self._circuit_breaker.is_open():
            return Err(CircuitOpenError(self._circuit_breaker.name))

        max_attempts = 2
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                payload: dict[str, str] = {
                    "grant_type": "client_credentials",
                    "client_id": self._settings.client_id,
                    "client_secret": self._settings.client_secret,
                }
                if self._settings.default_scope:
                    payload["scope"] = self._settings.default_scope

                async with httpx.AsyncClient(timeout=30) as auth_client:
                    response = await auth_client.post(
                        self._settings.auth_url,
                        data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                    response.raise_for_status()
                    data = response.json()

                self._token = _TactoToken(
                    access_token=data["access_token"],
                    token_type=data.get("token_type", "Bearer"),
                    expires_in=int(data.get("expires_in", 3600)),
                    obtained_at=time.time(),
                )

                logger.debug("Tacto token refreshed", expires_in=self._token.expires_in)
                self._circuit_breaker.record_success()
                return Ok(self._token.access_token)

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    "Tacto auth timeout",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    auth_url=self._settings.auth_url,
                    error=f"Request timed out after 30s: {type(e).__name__}",
                )
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    "Tacto auth connection error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    auth_url=self._settings.auth_url,
                    error=f"Connection failed: {repr(e)}",
                )
            except httpx.HTTPStatusError as e:
                # Non-retryable — bad credentials, wrong endpoint, etc.
                logger.error(
                    "Tacto auth failed",
                    status=e.response.status_code,
                    error=str(e),
                )
                self._circuit_breaker.record_failure()
                return Err(e)
            except Exception as e:
                last_error = e
                logger.warning(
                    "Tacto auth unexpected error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=repr(e),
                    error_type=type(e).__name__,
                )

            # Retry delay (only if not the last attempt)
            if attempt < max_attempts:
                logger.info("Retrying Tacto auth", delay_seconds=2)
                await asyncio.sleep(2)

        # All attempts exhausted
        logger.error(
            "Tacto auth failed after retries",
            attempts=max_attempts,
            error=repr(last_error),
        )
        self._circuit_breaker.record_failure()
        return Err(last_error or RuntimeError("Tacto auth failed: unknown error"))

    # ------------------------------------------------------------------ #
    # Request helpers                                                       #
    # ------------------------------------------------------------------ #

    def _build_headers(
        self,
        token: str,
        grupo_empresarial: str,
        empresa_id: str,
    ) -> dict[str, str]:
        """
        Build the full header set required by Tacto External API.

        Required headers (per Tacto documentation):
        - Authorization      : Bearer <token>
        - chave-origem       : exclusive integration key (TACTO_CHAVE_ORIGEM)
        - Tacto-Grupo-Empresarial : grupo empresarial key
        - EmpresaId          : company ID within the group
        - GrupoEmpresaId     : same as Tacto-Grupo-Empresarial
        - Tacto-Grupo-Empresa-Id : same as Tacto-Grupo-Empresarial
        """
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "chave-origem": self._settings.chave_origem,
            "Tacto-Grupo-Empresarial": grupo_empresarial,
            "EmpresaId": empresa_id,
            "GrupoEmpresaId": grupo_empresarial,
            "Tacto-Grupo-Empresa-Id": grupo_empresarial,
        }

    # ------------------------------------------------------------------ #
    # API methods                                                           #
    # ------------------------------------------------------------------ #

    async def get_rag_full(
        self,
        grupo_empresarial: str,
        empresa_base_id: str,
    ) -> Success[dict[str, Any]] | Failure[Exception]:
        """
        Fetch full RAG data for a restaurant (institutional + menu context).

        GET /v1/empresa/dados-institucionais/rag-full

        Args:
            grupo_empresarial: Chave do grupo empresarial (ChaveGrupoEmpresarial)
            empresa_base_id: Código da empresa dentro do grupo (EmpresaBaseId)
        """
        token_result = await self._ensure_token()
        if isinstance(token_result, Failure):
            return token_result

        try:
            self._ensure_client()

            response = await self._client.get(
                "/v1/empresa/dados-institucionais/rag-full",
                headers=self._build_headers(
                    token=token_result.value,
                    grupo_empresarial=grupo_empresarial,
                    empresa_id=empresa_base_id,
                ),
            )
            response.raise_for_status()
            self._circuit_breaker.record_success()
            return Ok(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(
                "Tacto RAG full fetch failed",
                status=e.response.status_code,
                empresa_base_id=empresa_base_id,
                error=str(e),
            )
            self._circuit_breaker.record_failure()
            return Err(e)
        except Exception as e:
            logger.error("Tacto RAG full error", error=str(e))
            self._circuit_breaker.record_failure()
            return Err(e)

    async def get_institutional_data(
        self,
        grupo_empresarial: str,
        empresa_base_id: str,
    ) -> Success[dict[str, Any]] | Failure[Exception]:
        """
        Fetch simplified institutional data (hours + basic info).

        GET /v1/empresa/dados-institucionais/wg
        """
        token_result = await self._ensure_token()
        if isinstance(token_result, Failure):
            return token_result

        try:
            self._ensure_client()

            response = await self._client.get(
                "/v1/empresa/dados-institucionais/wg",
                headers=self._build_headers(
                    token=token_result.value,
                    grupo_empresarial=grupo_empresarial,
                    empresa_id=empresa_base_id,
                ),
            )
            response.raise_for_status()
            self._circuit_breaker.record_success()
            return Ok(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(
                "Tacto institutional data fetch failed",
                status=e.response.status_code,
                empresa_base_id=empresa_base_id,
                error=str(e),
            )
            self._circuit_breaker.record_failure()
            return Err(e)
        except Exception as e:
            logger.error("Tacto institutional data error", error=str(e))
            self._circuit_breaker.record_failure()
            return Err(e)

    async def health_check(self) -> Success[bool] | Failure[Exception]:
        """Verify Tacto auth is working (token can be obtained)."""
        try:
            result = await self._fetch_token()
            return Ok(isinstance(result, Success))
        except Exception as e:
            return Err(e)

    # ------------------------------------------------------------------ #
    # Order Submission (Level 2 Agent)                                   #
    # ------------------------------------------------------------------ #

    async def submit_order(
        self,
        grupo_empresarial: str,
        empresa_base_id: str,
        order_payload: dict[str, Any],
    ) -> Success[dict[str, Any]] | Failure[Exception]:
        """
        Submit a new order to Tacto API.

        POST /v1/pedido/whatsapp

        Args:
            grupo_empresarial: Chave do grupo empresarial
            empresa_base_id: Código da empresa dentro do grupo
            order_payload: Order data following Tacto's schema:
                {
                    "cliente": {"telefone": str, "nome": str},
                    "enderecoEntrega": {"endereco": str, ...},
                    "formaPagamento": str,
                    "itens": [{name, quantidade, precoUnitario, ...}],
                    "subtotal": float,
                    "total": float,
                    "observacaoGeral": str,
                    "origem": "WHATSAPP_AI"
                }

        Returns:
            Success with order confirmation including Tacto order ID
            Failure with exception on error
        """
        token_result = await self._ensure_token()
        if isinstance(token_result, Failure):
            return token_result

        try:
            self._ensure_client()

            logger.info(
                "Submitting order to Tacto",
                empresa_base_id=empresa_base_id,
                item_count=len(order_payload.get("itens", [])),
                total=order_payload.get("total"),
            )

            response = await self._client.post(
                "/v1/pedido/whatsapp",
                headers=self._build_headers(
                    token=token_result.value,
                    grupo_empresarial=grupo_empresarial,
                    empresa_id=empresa_base_id,
                ),
                json=order_payload,
            )
            response.raise_for_status()
            self._circuit_breaker.record_success()

            result = response.json()
            logger.info(
                "Order submitted successfully",
                tacto_order_id=result.get("pedidoId") or result.get("id"),
                status=result.get("status"),
            )

            return Ok(result)

        except httpx.HTTPStatusError as e:
            error_body = None
            try:
                error_body = e.response.json()
            except Exception:
                error_body = e.response.text[:500] if e.response.text else None

            logger.error(
                "Tacto order submission failed",
                status=e.response.status_code,
                empresa_base_id=empresa_base_id,
                error=str(e),
                error_body=error_body,
            )
            self._circuit_breaker.record_failure()
            return Err(e)
        except Exception as e:
            logger.error(
                "Tacto order submission error",
                empresa_base_id=empresa_base_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            self._circuit_breaker.record_failure()
            return Err(e)

    async def get_order_status(
        self,
        grupo_empresarial: str,
        empresa_base_id: str,
        order_id: str,
    ) -> Success[dict[str, Any]] | Failure[Exception]:
        """
        Get order status from Tacto API.

        GET /v1/pedido/{order_id}/status

        Args:
            grupo_empresarial: Chave do grupo empresarial
            empresa_base_id: Código da empresa dentro do grupo
            order_id: Tacto order ID

        Returns:
            Success with order status data
            Failure with exception on error
        """
        token_result = await self._ensure_token()
        if isinstance(token_result, Failure):
            return token_result

        try:
            self._ensure_client()

            response = await self._client.get(
                f"/v1/pedido/{order_id}/status",
                headers=self._build_headers(
                    token=token_result.value,
                    grupo_empresarial=grupo_empresarial,
                    empresa_id=empresa_base_id,
                ),
            )
            response.raise_for_status()
            self._circuit_breaker.record_success()
            return Ok(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(
                "Tacto order status fetch failed",
                status=e.response.status_code,
                order_id=order_id,
                error=str(e),
            )
            self._circuit_breaker.record_failure()
            return Err(e)
        except Exception as e:
            logger.error("Tacto order status error", order_id=order_id, error=str(e))
            self._circuit_breaker.record_failure()
            return Err(e)
