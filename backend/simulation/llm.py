"""LLM provider abstraction (Phase 2). MVP uses stub / heuristic in engine."""

from __future__ import annotations

from config import get_settings


def describe_provider() -> dict[str, str]:
    settings = get_settings()
    return {
        "provider": settings.llm_provider,
        "ollama_model": settings.ollama_model,
        "openai_model": settings.openai_model,
        "note": "Decision currently uses heuristic stub; LLM wiring is Phase 2.",
    }
