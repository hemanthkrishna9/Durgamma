from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Mission Control"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./mission_control.db"
    openclaw_gateway_url: str = "ws://localhost:18789"
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"
    missions_dir: str = "./missions"
    agent_templates_dir: str = "../agent-templates"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {"env_prefix": "MC_", "env_file": ".env"}


settings = Settings()
