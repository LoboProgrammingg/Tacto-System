"""
Join Instance Manager.

Manages WhatsApp instances via Join Developer API (api-prd.joindeveloper.com.br).
Supports: create, list, connect, configure webhook, QR code, status.
"""

from dataclasses import dataclass
from typing import Any, Optional

import httpx
import structlog

from tacto.config import JoinAPISettings, get_settings
from tacto.shared.application import Err, Failure, Ok, Success


logger = structlog.get_logger()


@dataclass
class JoinInstance:
    """Represents a Join WhatsApp instance."""

    instance_key: str
    status: str
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None
    is_connected: bool = False


@dataclass
class QRCodeResponse:
    """QR Code response from Join API."""

    qr_code: str
    instance_key: str
    expires_in: int = 60


class JoinInstanceManager:
    """
    Manages Join Developer WhatsApp instances.

    All credentials come from environment via JoinAPISettings.
    Authentication via `tokenCliente` header on every request.
    """

    def __init__(self, settings: Optional[JoinAPISettings] = None) -> None:
        self._settings = settings or get_settings().join
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> Success[bool] | Failure[Exception]:
        """Initialize HTTP client."""
        try:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=self._settings.http_timeout,
                headers=self._get_headers(),
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

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "tokenCliente": self._settings.token_cliente,
        }

    def _ensure_client(self) -> None:
        """Lazy-init HTTP client if not already connected."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=self._settings.http_timeout,
                headers=self._get_headers(),
            )

    def _parse_instance(self, item: dict[str, Any]) -> JoinInstance:
        """
        Parse a raw API dict into a JoinInstance.

        Actual Join API response format:
        {
          "nome": "wp-empresa-7",
          "status": "open",
          "token_instancia": "51952e2c-...",
          "numero_conectado": "554187273618"
        }
        """
        status = item.get("status", "unknown")
        return JoinInstance(
            instance_key=item.get("token_instancia", item.get("nome", "")),
            status=status,
            phone_number=item.get("numero_conectado", item.get("numero")),
            webhook_url=item.get("webhookUrl"),
            is_connected=status == "open",
        )

    async def list_instances(self) -> Success[list[JoinInstance]] | Failure[Exception]:
        """
        List all available instances for this token_cliente.

        GET /instancias/listarinstancias
        Response: {"Quantidade": N, "Instancias": [...]}
        """
        try:
            self._ensure_client()

            response = await self._client.get("/instancias/listarinstancias")
            response.raise_for_status()
            data = response.json()

            # Join API returns "Instancias" (capital I)
            raw_list = data.get("Instancias", data.get("instancias", []))
            if isinstance(data, list):
                raw_list = data

            instances = [self._parse_instance(item) for item in raw_list]

            return Ok(instances)

        except Exception as e:
            logger.error("Failed to list instances", error=str(e))
            return Err(e)

    async def create_instance(
        self, instance_name: str
    ) -> Success[JoinInstance] | Failure[Exception]:
        """
        Create a new WhatsApp instance.

        POST /instancias/criarinstancia
        """
        try:
            self._ensure_client()

            response = await self._client.post(
                "/instancias/criarinstancia",
                json={"instancia": instance_name},
            )
            response.raise_for_status()
            data = response.json()

            instance = JoinInstance(
                instance_key=data.get("chave", data.get("instanceKey", data.get("key", ""))),
                status="created",
                is_connected=False,
            )

            logger.info("Instance created", instance_key=instance.instance_key)
            return Ok(instance)

        except httpx.HTTPStatusError as e:
            logger.error("Failed to create instance", error=str(e))
            return Err(e)
        except Exception as e:
            logger.error("Instance creation error", error=str(e))
            return Err(e)

    async def get_instance_status(
        self, instance_key: str
    ) -> Success[JoinInstance] | Failure[Exception]:
        """
        Get connection status of a specific instance.

        GET /instancias/statusconexao?chave={instance_key}
        """
        try:
            self._ensure_client()

            response = await self._client.get(
                "/instancias/statusconexao",
                params={"chave": instance_key},
            )
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "unknown")
            instance = JoinInstance(
                instance_key=instance_key,
                status=status,
                phone_number=data.get("numero", data.get("phoneNumber")),
                webhook_url=data.get("webhookUrl"),
                is_connected=status in ("connected", "open", "ativo"),
            )

            return Ok(instance)

        except Exception as e:
            logger.error("Failed to get instance status", error=str(e))
            return Err(e)

    async def get_qr_code(
        self, instance_key: str
    ) -> Success[QRCodeResponse] | Failure[Exception]:
        """
        Get QR code / instance info for WhatsApp connection.

        GET /webhook/infoinstancia?chave={instance_key}
        """
        try:
            self._ensure_client()

            response = await self._client.get(
                "/webhook/infoinstancia",
                params={"chave": instance_key},
            )
            response.raise_for_status()
            data = response.json()

            qr_raw = (
                data.get("qrcode")
                or data.get("qrCode")
                or data.get("base64")
                or ""
            )

            if not qr_raw:
                return Err(RuntimeError("No QR code available — instance may already be connected"))

            return Ok(
                QRCodeResponse(
                    qr_code=qr_raw,
                    instance_key=instance_key,
                    expires_in=data.get("expiresIn", 60),
                )
            )

        except Exception as e:
            logger.error("Failed to get QR code", error=str(e))
            return Err(e)

    async def configure_webhook(
        self,
        instance_key: str,
        webhook_url: str,
        events: Optional[list[str]] = None,
    ) -> Success[bool] | Failure[Exception]:
        """Configure webhook URL for an instance.

        POST /webhook/configurarinstancia
        Headers: tokenCliente, instancia (instance name)
        Body: {"url": webhook_url}
        """
        try:
            self._ensure_client()

            response = await self._client.post(
                "/webhook/configurarinstancia",
                headers={
                    **self._get_headers(),
                    "instancia": instance_key,
                },
                json={"url": webhook_url},
            )
            response.raise_for_status()

            logger.info("Webhook configured", instance_key=instance_key, webhook_url=webhook_url)
            return Ok(True)

        except Exception as e:
            logger.error("Failed to configure webhook", error=str(e))
            return Err(e)

    async def disconnect_instance(
        self, instance_key: str
    ) -> Success[bool] | Failure[Exception]:
        """Disconnect/logout an instance."""
        try:
            self._ensure_client()

            response = await self._client.post(
                "/instancias/desconectar",
                json={"chave": instance_key},
            )
            response.raise_for_status()

            logger.info("Instance disconnected", instance_key=instance_key)
            return Ok(True)

        except Exception as e:
            logger.error("Failed to disconnect instance", error=str(e))
            return Err(e)

    async def delete_instance(
        self, instance_key: str
    ) -> Success[bool] | Failure[Exception]:
        """Delete an instance."""
        try:
            self._ensure_client()

            response = await self._client.post(
                "/instancias/deletar",
                json={"chave": instance_key},
            )
            response.raise_for_status()

            logger.info("Instance deleted", instance_key=instance_key)
            return Ok(True)

        except Exception as e:
            logger.error("Failed to delete instance", error=str(e))
            return Err(e)
