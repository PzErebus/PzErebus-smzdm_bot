"""Configuration management for SMZDM Bot.

Configuration is loaded from environment variables using Pydantic Settings.

Environment Variables:
    SMZDM_COOKIE: Cookie string (single user mode)
    SMZDM_SK: Optional security key
    SMZDM_USERS: JSON array for multi-user mode
        Example: '[{"cookie": "...", "sk": "..."}, {"cookie": "..."}]'

    Notification:
    SMZDM_PUSH_PLUS_TOKEN: PushPlus token
    SMZDM_SC_KEY: ServerChan key
    SMZDM_WECOM_WEBHOOK: WeCom bot webhook URL
    SMZDM_TG_BOT_TOKEN: Telegram bot token
    SMZDM_TG_USER_ID: Telegram user/chat ID
    SMZDM_TG_API_BASE: Custom Telegram API base URL

    青龙面板标准变量（自动识别）:
    PUSH_PLUS_TOKEN: PushPlus token
    SCKEY: ServerChan key
    TG_BOT_TOKEN: Telegram bot token
    TG_USER_ID: Telegram user/chat ID
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from smzdm_bot.exceptions import ConfigurationError


def _find_dotenv() -> Path | None:
    """Find .env file by searching up from cwd or using package location."""
    cwd = Path.cwd()
    if (cwd / ".env").exists():
        return cwd / ".env"

    pkg_dir = Path(__file__).parent.parent.parent.parent
    if (pkg_dir / ".env").exists():
        return pkg_dir / ".env"

    return None


class UserConfig(BaseModel):
    """Configuration for a single user account."""

    cookie: str
    sk: str = ""
    name: str = ""

    @field_validator("cookie")
    @classmethod
    def validate_cookie(cls, v: str) -> str:
        """Ensure cookie is not empty."""
        if not v or not v.strip():
            raise ValueError("Cookie cannot be empty")
        return v.strip()


class NotifyConfig(BaseModel):
    """Notification service configuration."""

    push_plus_token: str = ""
    sc_key: str = ""
    wecom_webhook: str = ""
    tg_bot_token: str = ""
    tg_user_id: str = ""
    tg_api_base: str = ""

    @property
    def has_any_provider(self) -> bool:
        """Check if at least one notification provider is configured."""
        return any(
            [
                self.push_plus_token,
                self.sc_key,
                self.wecom_webhook,
                self.tg_bot_token and self.tg_user_id,
            ]
        )


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    cookie: str = ""
    sk: str = ""
    users: str = ""

    push_plus_token: str = ""
    sc_key: str = ""
    wecom_webhook: str = ""
    tg_bot_token: str = ""
    tg_user_id: str = ""
    tg_api_base: str = ""

    debug: bool = False

    model_config = SettingsConfigDict(
        env_prefix="SMZDM_",
        env_file=_find_dotenv(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("push_plus_token", mode="before")
    @classmethod
    def validate_push_plus_token(cls, v: str) -> str:
        """优先使用脚本变量，其次使用青龙面板变量。"""
        if v:
            return v
        # 青龙面板标准变量
        return os.environ.get("PUSH_PLUS_TOKEN", "")

    @field_validator("sc_key", mode="before")
    @classmethod
    def validate_sc_key(cls, v: str) -> str:
        """优先使用脚本变量，其次使用青龙面板变量。"""
        if v:
            return v
        # 青龙面板标准变量
        return os.environ.get("SCKEY", "")

    @field_validator("tg_bot_token", mode="before")
    @classmethod
    def validate_tg_bot_token(cls, v: str) -> str:
        """优先使用脚本变量，其次使用青龙面板变量。"""
        if v:
            return v
        # 青龙面板标准变量
        return os.environ.get("TG_BOT_TOKEN", "")

    @field_validator("tg_user_id", mode="before")
    @classmethod
    def validate_tg_user_id(cls, v: str) -> str:
        """优先使用脚本变量，其次使用青龙面板变量。"""
        if v:
            return v
        # 青龙面板标准变量
        return os.environ.get("TG_USER_ID", "")

    def get_users(self) -> list[UserConfig]:
        """Get list of user configurations."""
        users: list[UserConfig] = []

        if self.users:
            try:
                users_data = json.loads(self.users)
                if isinstance(users_data, list):
                    for i, user_data in enumerate(users_data):
                        if isinstance(user_data, dict) and user_data.get("cookie"):
                            users.append(
                                UserConfig(
                                    cookie=user_data["cookie"],
                                    sk=user_data.get("sk", ""),
                                    name=user_data.get("name", f"User{i + 1}"),
                                )
                            )
            except json.JSONDecodeError as e:
                raise ConfigurationError(
                    f"Invalid SMZDM_USERS JSON format: {e}",
                    details={"users": self.users[:100]},
                ) from e

        if not users and self.cookie:
            users.append(
                UserConfig(
                    cookie=self.cookie,
                    sk=self.sk,
                    name="default",
                )
            )

        if not users:
            raise ConfigurationError(
                "No users configured. Set SMZDM_COOKIE or SMZDM_USERS environment variable.",
            )

        return users

    def get_notify_config(self) -> NotifyConfig:
        """Get notification configuration."""
        return NotifyConfig(
            push_plus_token=self.push_plus_token,
            sc_key=self.sc_key,
            wecom_webhook=self.wecom_webhook,
            tg_bot_token=self.tg_bot_token,
            tg_user_id=self.tg_user_id,
            tg_api_base=self.tg_api_base,
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings


__all__ = [
    "NotifyConfig",
    "Settings",
    "UserConfig",
    "get_settings",
    "reload_settings",
]
