from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM providers
    groq_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # Research
    tavily_api_key: str = ""

    # Notifications
    ntfy_topic: str = ""

    # LangSmith
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "false"
    langchain_project: str = "social-branding-agent"

    # App
    app_data_dir: Path = Path.home() / ".social-branding-agent"
    backend_port: int = 8000

    @property
    def db_path(self) -> Path:
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        return self.app_data_dir / "app.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


settings = Settings()
