from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "stub"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Cap LLM calls so large populations stay demoable (rest use heuristics).
    llm_max_agents_per_turn: int = 4  # legacy; group mode ignores this
    llm_timeout_sec: float = 8.0
    llm_concurrency: int = 1
    # Group/institution stance: sample this many actors per region to enact policy.
    llm_group_sample_per_region: int = 12
    # Narrative language for summary / reason fields shown in the UI (ja|en).
    llm_narrative_lang: str = "ja"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
