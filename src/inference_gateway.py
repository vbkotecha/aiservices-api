"""
LLM Inference Gateway — x402-paid proxy for AI model inference.
Direct competitor to BlockRun.ai (~$820/day revenue).

Agents pay per inference call via x402. We proxy to multiple providers:
- CodexSale (OpenAI-compatible): gpt-5.4, gpt-5.4-mini, gpt-5.5
- Google Gemini (AI Studio): gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro

Margin model: we charge $0.03-$0.05 per call, backend costs less.
Gemini has a generous free tier (15 RPM, 1500/day) — highest margin.

CodexSale models: gpt-5.4, gpt-5.4-mini, gpt-5.5
Gemini models: gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro
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

# Load Gemini API key (optional — from env or key file)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini_key_file = Path("/root/.letta/keys/gemini.key")
if not GEMINI_KEY and _gemini_key_file.exists():
    GEMINI_KEY = _gemini_key_file.read_text().strip()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

AVAILABLE_MODELS = [
    {"id": "gpt-5.4", "description": "Most capable GPT — complex reasoning, code, analysis"},
    {"id": "gpt-5.4-mini", "description": "Fast GPT — good for most tasks"},
    {"id": "gpt-5.5", "description": "Latest GPT — highest quality outputs"},
    {"id": "gemini-2.0-flash", "description": "Google Gemini 2.0 Flash — fast, multimodal, cost-effective"},
    {"id": "gemini-2.5-flash", "description": "Google Gemini 2.5 Flash — balanced speed and quality"},
    {"id": "gemini-2.5-pro", "description": "Google Gemini 2.5 Pro — highest quality reasoning"},
]


def list_models():
    """List available models for inference."""
    return {
        "models": AVAILABLE_MODELS,
        "default": "gpt-5.4-mini",
        "providers": {
            "codexsale": ["gpt-5.4", "gpt-5.4-mini", "gpt-5.5"],
            "gemini": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"] if GEMINI_KEY else [],
        },
        "pricing": "$0.03 per call via x402 (USDC on Base)",
        "provider": "AgentServices inference gateway",
        "note": "OpenAI-compatible API. Send chat completion requests to POST /v1/inference. Gemini models also accepted.",
    }


def inference(
    model: str = "gpt-5.4-mini",
    messages: list = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    stream: bool = False,
):
    """
    Proxy a chat completion request to the appropriate backend.
    Agents pay $0.03 via x402 before this executes.

    Routes to Gemini API for gemini-* models, CodexSale for gpt-* models.

    Args:
        model: gpt-5.4, gpt-5.4-mini, gpt-5.5, gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro
        messages: List of {role, content} messages (OpenAI format)
        temperature: 0.0-2.0 sampling temperature
        max_tokens: Max tokens to generate
        stream: If True, returns streaming response
    """
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

    # Route to Gemini if model starts with gemini-
    if model.startswith("gemini-"):
        return _call_gemini(model, messages, temperature, max_tokens)

    # Route to CodexSale for GPT models
    if not CODEXSALE_KEY:
        return {"error": "Inference backend not configured", "status": "error"}

    return _call_codexsale(model, messages, temperature, max_tokens, stream)


def _call_gemini(model, messages, temperature, max_tokens):
    """Call Google Gemini API with OpenAI-format message conversion."""
    if not GEMINI_KEY:
        return {
            "error": "Gemini backend not configured. Set GEMINI_API_KEY env var.",
            "status": "backend_not_configured",
            "fallback": "Use gpt-5.4-mini or gpt-5.5 instead.",
        }

    # Convert OpenAI messages → Gemini contents format
    contents = []
    system_instruction = None
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    try:
        req_data = json.dumps(payload).encode("utf-8")
        url = f"{GEMINI_BASE_URL}/models/{model}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        # Convert Gemini response → OpenAI-compatible format
        candidates = result.get("candidates", [])
        text_parts = []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text_parts = [p.get("text", "") for p in parts]

        # Return OpenAI-compatible format so agents don't need to handle two APIs
        return {
            "id": f"agentservices-gemini-{model}",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "".join(text_parts)},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": result.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": result.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                "total_tokens": result.get("usageMetadata", {}).get("totalTokenCount", 0),
            },
            "provider": "AgentServices Inference Gateway (Google Gemini)",
            "model_requested": model,
            "x402_paid": True,
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {
            "error": f"Gemini backend error: {e.code} {e.reason}",
            "details": error_body[:500],
            "status": "backend_error",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


def _call_codexsale(model, messages, temperature, max_tokens, stream):
    """Proxy to CodexSale (OpenAI-compatible) for GPT models."""
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
