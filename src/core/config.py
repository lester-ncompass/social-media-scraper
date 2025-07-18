import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """
    Application settings, loaded from environment variables and .env file.
    Defines configurations for API keys, service URLs, server behavior, and prompts.
    Args:
        BaseSettings (_type_): Base class for settings management.
    """

    # --- Server Configuration (for Uvicorn) ---
    APP_HOST: str = Field("localhost", validation_alias="APP_HOST")
    APP_PORT: int = Field(8000, validation_alias="APP_PORT")
    DEBUG_MODE: bool = Field(
        False, validation_alias="DEBUG_MODE"
    )  # For Uvicorn reload and verbose logging
    LOG_LEVEL: str = Field(
        "INFO", validation_alias="LOG_LEVEL"
    )  # e.g., DEBUG, INFO, WARNING, ERROR
    INSTAGRAM_COOKIES: str = Field("", validation_alias="INSTAGRAM_COOKIES")
    TIKTOK_COOKIES: str = Field("", validation_alias="TIKTOK_COOKIES")
    TEXT_PROMPT_MODEL_NAME: str = Field("", validation_alias="TEXT_PROMPT_MODEL_NAME")
    PREPROMPT_FILE_PATH: str = Field(
        os.path.join("assets", "preprompt"), validation_alias="PREPROMPT_FILE_PATH"
    )
    GOOGLE_API_KEY: str = Field("", validation_alias="GOOGLE_API_KEY")
    APIFY_KEY: str = Field("", validation_alias="APIFY_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from .env rather than raising an error
        case_sensitive=False,  # Environment variables are often uppercase
    )


config = Config()  # type: ignore
