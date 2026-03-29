#!/usr/bin/env python3
"""
Script para capturar e analisar payload completo da Join API.

Execute este script como um servidor temporário para capturar o payload real.
Configure o webhook da Join para apontar para este endpoint.

Usage:
    python scripts/capture_join_payload.py

Depois:
1. Configure webhook da Join para: http://SEU_IP:8888/webhook
2. Envie uma mensagem DO CELULAR conectado na instância (fromMe=true)
3. O payload completo será salvo em join_payload_from_me.json
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
import uvicorn


app = FastAPI(title="Join Payload Capture")

CAPTURE_DIR = Path(__file__).parent / "captured_payloads"
CAPTURE_DIR.mkdir(exist_ok=True)


@app.post("/webhook")
@app.post("/webhook/join")
@app.post("/webhook/join/")
async def capture_webhook(request: Request):
    """Captura e salva o payload completo do webhook."""
    try:
        body = await request.json()
    except Exception:
        body = {"error": "Could not parse JSON", "raw": await request.body()}
    
    # Extrair informações chave
    event = body.get("event", "unknown")
    instance = body.get("instance", "unknown")
    data = body.get("data", {})
    key = data.get("key", {})
    from_me = key.get("fromMe", False)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Nome do arquivo baseado no tipo de mensagem
    if from_me:
        filename = f"FROM_ME_{timestamp}.json"
        print("\n" + "="*60)
        print("🔴 MENSAGEM FROM_ME CAPTURADA!")
        print("="*60)
    else:
        filename = f"FROM_CUSTOMER_{timestamp}.json"
        print("\n" + "-"*60)
        print("📥 Mensagem do cliente capturada")
        print("-"*60)
    
    filepath = CAPTURE_DIR / filename
    
    # Salvar payload completo
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"📁 Salvo em: {filepath}")
    print(f"📋 Event: {event}")
    print(f"📋 Instance: {instance}")
    print(f"📋 fromMe: {from_me}")
    
    # Mostrar TODAS as chaves do payload
    print(f"\n🔍 CHAVES NO BODY: {list(body.keys())}")
    print(f"🔍 CHAVES NO DATA: {list(data.keys())}")
    print(f"🔍 CHAVES NO KEY: {list(key.keys())}")
    
    # Se fromMe, mostrar detalhes importantes
    if from_me:
        print("\n📱 CAMPOS POTENCIAIS PARA NÚMERO DA INSTÂNCIA:")
        print(f"   - instance: {instance}")
        print(f"   - data.owner: {data.get('owner')}")
        print(f"   - data.source: {data.get('source')}")
        print(f"   - data.participant: {data.get('participant')}")
        print(f"   - key.participant: {key.get('participant')}")
        print(f"   - key.remoteJid: {key.get('remoteJid')}")
        print(f"   - body.sender: {body.get('sender')}")
        print(f"   - body.owner: {body.get('owner')}")
        
        # Verificar se existe algum campo com o número da instância
        print("\n🔎 PROCURANDO CAMPOS COM NÚMEROS DE TELEFONE:")
        _find_phone_fields(body, prefix="body")
    
    print("="*60 + "\n")
    
    return {"success": True, "saved": str(filepath)}


def _find_phone_fields(obj, prefix=""):
    """Recursivamente procura campos que parecem ser números de telefone."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str) and ("@" in value or value.isdigit()):
                if len(value) > 8:  # Provavelmente um número
                    print(f"   📞 {new_prefix}: {value}")
            elif isinstance(value, (dict, list)):
                _find_phone_fields(value, new_prefix)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _find_phone_fields(item, f"{prefix}[{i}]")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 SERVIDOR DE CAPTURA DE PAYLOAD DA JOIN API")
    print("="*60)
    print("\nInstruções:")
    print("1. Configure o webhook da Join para: http://SEU_IP:8888/webhook/join")
    print("2. Envie uma mensagem DO CELULAR conectado na instância")
    print("3. O payload completo será salvo em scripts/captured_payloads/")
    print("\nPressione Ctrl+C para parar")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8888)
