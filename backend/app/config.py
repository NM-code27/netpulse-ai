from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./netpulse.db"

    llm_provider: str = "ollama"  # "ollama" (local, free) or "groq" (free cloud fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # The live simulator runs simulated-minutes this many times faster than
    # real time. Fault ramps (e.g. a 12-simulated-minute link degradation)
    # are tuned for realism in the historical training data, where "minutes"
    # are just a tick count -- but a live portfolio demo can't make a visitor
    # wait 12 real minutes to see a fault reach full effect. Speeding up the
    # live clock keeps the exact same model/threshold semantics while making
    # "inject a fault -> watch the risk score climb" happen in under 2 minutes.
    live_speed_multiplier: float = 8.0
    # Chosen so simulator_tick_seconds * live_speed_multiplier / 60 == 2.0 --
    # the same 2-simulated-minutes-per-sample resolution the historical
    # dataset was generated at (app/simulator/historical.py), so the rolling
    # features (roll_mean_5, rate_of_change, ...) the live scoring loop
    # computes see the same per-step time delta the models were trained on.
    simulator_tick_seconds: float = 15.0
    scoring_interval_seconds: float = 30.0
    forecast_horizon_minutes: int = 30

    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
