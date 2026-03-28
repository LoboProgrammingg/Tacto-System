#!/usr/bin/env python3
"""
Configure Join webhook URL for a WhatsApp instance.

Join API endpoint: POST /webhook/configurarinstancia
Headers: tokenCliente + instancia
Body: {"url": "https://your-ngrok-url/api/v1/webhook/join/"}

Usage:
    python scripts/configure_webhook.py --instance wp-empresa-7 --url https://xxxx.ngrok-free.app/api/v1/webhook/join/
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def configure_webhook(instance_key: str, webhook_url: str) -> None:
    import httpx
    from dotenv import load_dotenv

    load_dotenv()

    from tacto.config import get_settings

    settings = get_settings()
    token = settings.join.token_cliente
    base_url = settings.join.base_url

    if not token:
        print("❌ JOIN_TOKEN_CLIENTE not set in .env")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "tokenCliente": token,
        "instancia": instance_key,
    }

    payload = {"url": webhook_url}

    print(f"🔧 Configuring webhook")
    print(f"   Instance : {instance_key}")
    print(f"   Webhook  : {webhook_url}")
    print(f"   Endpoint : {base_url}/webhook/configurarinstancia")

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        response = await client.post(
            "/webhook/configurarinstancia",
            json=payload,
            headers=headers,
        )

    print(f"\n   HTTP Status: {response.status_code}")

    try:
        data = response.json()
        print(f"   Response  : {data}")
    except Exception:
        print(f"   Response text: {response.text}")

    if response.status_code in (200, 201):
        print(f"\n✅ Webhook configured!")
        print(f"   '{instance_key}' → {webhook_url}")
    else:
        print(f"\n❌ Failed (HTTP {response.status_code})")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Join webhook URL")
    parser.add_argument("--instance", required=True, help="Instance name (e.g. wp-empresa-7)")
    parser.add_argument("--url", required=True, help="Webhook URL (public, e.g. https://xxx.ngrok-free.app/api/v1/webhook/join/)")
    args = parser.parse_args()

    asyncio.run(configure_webhook(args.instance, args.url))


if __name__ == "__main__":
    main()
