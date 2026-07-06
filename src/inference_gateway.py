"""
LLM Inference Gateway — x402-paid proxy for AI model inference.
Direct competitor to BlockRun.ai (~$820/day revenue).

Agents pay per inference call via x402. We proxy to CodexSale (OpenAI-compatible).
Margin model: we charge $0.03-$0.05 per call, backend costs less.

CodexSale models: gpt-5.4, gpt-5.4-mini, gpt-5.5
OpenAI-compatible API at https://codex.sale/v1
"""
import urllib.request
import json
import os
from pathlib import Path

# Load CodexSale API key
_key_file = Path("/root/.letta/keys/codex_sale.key")
CODEXSALE_KEY = ""
if _key_file.exists():
    CODEXSALE_KEY = _key_file.read_text().strip()

CODEXSALE_BASE_URL = "https://codex.sale/v1"

AVAILABLE_MODELS = [
    {"id": "gpt-5.4", "description": "Most capable model — complex reasoning, code, analysis"},
    {"id": "gpt-5.4-mini", "description": "Fast and efficient — good for most tasks"},
    {"id": "gpt-5.5", "description": "Latest model — highest quality outputs"},
]


def list_models():
    """List available models for inference."""
    return {
        "models": AVAILABLE_MODELS,
        "default": "gpt-5.4-mini",
        "pricing": "$0.03 per call via x402 (USDC on Base)",
        "provider": "AgentServices inference gateway",
        "note": "OpenAI-compatible API. Send chat completion requests to POST /v1/inference.",
    }


def inference(
    model: str = "gpt-5.4-mini",
    messages: list = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    stream: bool = False,
):
    """
    Proxy a chat completion request to CodexSale.
    Agents pay $0.03 via x402 before this executes.

    Args:
        model: gpt-5.4, gpt-5.4-mini, or gpt-5.5
        messages: List of {role, content} messages (OpenAI format)
        temperature: 0.0-2.0 sampling temperature
        max_tokens: Max tokens to generate
        stream: If True, returns streaming response
    """
    if not CODEXSALE_KEY:
        return {"error": "Inference backend not configured", "status": "error"}

    if messages is None:
        messages = []

    # Validate model
    valid_models = [m["id"] for m in AVAILABLE_MODELS]
    if model not in valid_models:
        return {
            "error": f"Model '{model}' not available. Choose from: {valid_models}",
            "status": "invalid_model",
            "available_models": valid_models,
        }

    # Build request to CodexSale
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,  # We don't stream through x402
    }

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{CODEXSALE_BASE_URL}/chat/completions",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {CODEXSALE_KEY}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        # Add our metadata
        result["provider"] = "AgentServices Inference Gateway"
        result["model_requested"] = model
        result["x402_paid"] = True

        return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {
            "error": f"Backend error: {e.code} {e.reason}",
            "details": error_body[:500],
            "status": "backend_error",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


def quick_complete(prompt: str, model: str = "gpt-5.4-mini", max_tokens: int = 500):
    """
    Simple text completion — agent sends a prompt string, gets a response.
    Convenience wrapper for agents that don't want to build message arrays.

    $0.03 per call via x402.
    """
    messages = [{"role": "user", "content": prompt}]
    return inference(model=model, messages=messages, max_tokens=max_tokens)
