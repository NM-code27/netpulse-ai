"""
Provider switch for the troubleshooting assistant's LLM calls. Local Ollama
is free and fully offline for development; Groq's free API is the fallback
so the *deployed* demo (which can't reach your laptop's Ollama) still has a
working assistant. Both are free -- this never calls a paid API.
"""
import httpx

from app.config import settings


class LLMUnavailableError(RuntimeError):
    pass


def complete(prompt: str, system: str = "", temperature: float = 0.2) -> str:
    if settings.llm_provider == "groq":
        return _complete_groq(prompt, system, temperature)
    return _complete_ollama(prompt, system, temperature)


def _complete_ollama(prompt: str, system: str, temperature: float) -> str:
    try:
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except (httpx.HTTPError, httpx.ConnectError) as e:
        raise LLMUnavailableError(
            f"Could not reach local Ollama at {settings.ollama_base_url}. "
            f"Is `ollama serve` running and have you pulled {settings.ollama_model}? ({e})"
        ) from e


def _complete_groq(prompt: str, system: str, temperature: float) -> str:
    if not settings.groq_api_key:
        raise LLMUnavailableError("LLM_PROVIDER=groq but GROQ_API_KEY is not set.")
    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except httpx.HTTPError as e:
        raise LLMUnavailableError(f"Groq API call failed: {e}") from e
