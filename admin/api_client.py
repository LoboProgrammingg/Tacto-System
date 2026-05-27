"""HTTP clients for TactoFlow backend and Join Developer API.

Each method returns a tuple ``(ok: bool, payload)``:
- on success, ``payload`` is the parsed JSON body (dict or list);
- on failure, ``payload`` is a short error string suitable for display.
"""

from __future__ import annotations

from typing import Any, Optional

import requests


JsonResult = tuple[bool, Any]

DEFAULT_TIMEOUT = 15
HEALTH_TIMEOUT = 3
SYNC_TIMEOUT = 180


def _parse(response: requests.Response) -> JsonResult:
    try:
        body = response.json()
    except ValueError:
        body = response.text
    if response.ok:
        return True, body
    detail = body.get("detail") if isinstance(body, dict) else body
    return False, f"HTTP {response.status_code}: {detail}"


class TactoFlowClient:
    """Wrapper around the TactoFlow FastAPI backend."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    def health(self) -> JsonResult:
        try:
            r = requests.get(f"{self._base}/health", timeout=HEALTH_TIMEOUT)
            return _parse(r)
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"

    def list_restaurants(self) -> JsonResult:
        try:
            r = requests.get(
                f"{self._base}/api/v1/restaurants/",
                headers=self._headers,
                timeout=DEFAULT_TIMEOUT,
            )
            return _parse(r)
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"

    def create_restaurant(
        self,
        *,
        name: str,
        menu_url: str,
        chave_grupo_empresarial: str,
        canal_master_id: str,
        empresa_base_id: str,
        attendant_name: Optional[str] = None,
        attendant_gender: Optional[str] = None,
        persona_style: Optional[str] = None,
        max_emojis_per_message: Optional[int] = None,
        integration_type: int = 2,
        automation_type: int = 1,
    ) -> JsonResult:
        payload: dict[str, Any] = {
            "name": name,
            "menu_url": menu_url,
            "chave_grupo_empresarial": chave_grupo_empresarial.lower(),
            "canal_master_id": canal_master_id,
            "empresa_base_id": empresa_base_id,
            "integration_type": integration_type,
            "automation_type": automation_type,
        }
        agent_config: dict[str, Any] = {}
        if attendant_name:
            agent_config["attendant_name"] = attendant_name
        if attendant_gender:
            agent_config["attendant_gender"] = attendant_gender
        if persona_style:
            agent_config["persona_style"] = persona_style
        if max_emojis_per_message is not None:
            agent_config["max_emojis_per_message"] = max_emojis_per_message
        if agent_config:
            payload["agent_config"] = agent_config
        try:
            r = requests.post(
                f"{self._base}/api/v1/restaurants/",
                headers=self._headers,
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            return _parse(r)
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"

    def update_restaurant(
        self,
        restaurant_id: str,
        *,
        name: Optional[str] = None,
        menu_url: Optional[str] = None,
        prompt_default: Optional[str] = None,
        automation_type: Optional[int] = None,
        integration_type: Optional[int] = None,
        is_active: Optional[bool] = None,
        agent_config: Optional[dict[str, Any]] = None,
    ) -> JsonResult:
        """Partial update of a restaurant. Only non-None fields are sent.

        ``agent_config`` semantics:
          - ``None``  → field omitted (persona untouched).
          - ``{}``    → clears all persona overrides (uses platform defaults).
          - ``{...}`` → replaces persona overrides with the provided keys.
        """
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if menu_url is not None:
            payload["menu_url"] = menu_url
        if prompt_default is not None:
            payload["prompt_default"] = prompt_default
        if automation_type is not None:
            payload["automation_type"] = automation_type
        if integration_type is not None:
            payload["integration_type"] = integration_type
        if is_active is not None:
            payload["is_active"] = is_active
        if agent_config is not None:
            payload["agent_config"] = agent_config

        if not payload:
            return False, "Nada para atualizar."

        try:
            r = requests.patch(
                f"{self._base}/api/v1/restaurants/{restaurant_id}",
                headers=self._headers,
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            return _parse(r)
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"

    def tacto_sync(self, restaurant_id: str) -> JsonResult:
        try:
            r = requests.post(
                f"{self._base}/api/v1/restaurants/{restaurant_id}/tacto-sync",
                headers=self._headers,
                timeout=SYNC_TIMEOUT,
            )
            return _parse(r)
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"


class JoinClient:
    """Wrapper around the Join Developer API."""

    def __init__(self, base_url: str, token_cliente: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {
            "tokenCliente": token_cliente,
            "Content-Type": "application/json",
        }

    def list_instances(self) -> JsonResult:
        try:
            r = requests.get(
                f"{self._base}/instancias/listarinstancias",
                headers=self._headers,
                timeout=DEFAULT_TIMEOUT,
            )
            ok, body = _parse(r)
            if not ok:
                return ok, body
            instances = body.get("Instancias", []) if isinstance(body, dict) else []
            return True, instances
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"

    def create_instance(self, nome: str) -> JsonResult:
        try:
            r = requests.post(
                f"{self._base}/instancias/criarinstancia",
                headers=self._headers,
                json={"instancia": nome},
                timeout=DEFAULT_TIMEOUT,
            )
            ok, body = _parse(r)
            if not ok:
                return ok, body
            data = body[0] if isinstance(body, list) and body else body
            if isinstance(data, dict) and data.get("erro"):
                return False, str(data["erro"])
            return True, data
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"

    def configure_webhook(self, nome: str, webhook_url: str) -> JsonResult:
        headers = {**self._headers, "instancia": nome}
        try:
            r = requests.post(
                f"{self._base}/webhook/configurarinstancia",
                headers=headers,
                json={"url": webhook_url},
                timeout=DEFAULT_TIMEOUT,
            )
            ok, body = _parse(r)
            if not ok:
                return ok, body
            if isinstance(body, dict) and (body.get("error") or body.get("erro")):
                return False, str(body.get("error") or body.get("erro"))
            return True, body
        except requests.RequestException as exc:
            return False, f"Connection error: {exc}"
