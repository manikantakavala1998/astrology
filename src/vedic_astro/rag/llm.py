"""Chat completion via Ollama's local /api/chat endpoint - no network calls,
Ollama runs entirely on 127.0.0.1.
"""

from __future__ import annotations

import httpx

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
# qwen2.5:7b was the original target model but its download stalled badly on
# this network (~30KB/s, 4.7GB); using the already-downloaded, working
# llama3.2 for now. Swap this constant (or pass model=... explicitly) once
# qwen2.5 is available - nothing else in this module depends on which model.
CHAT_MODEL = "llama3.2"


def chat(
    system_prompt: str,
    user_message: str,
    model: str = CHAT_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = 120.0,
) -> str:
    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Ollama chat error: {data['error']}")
    return str(data["message"]["content"])
