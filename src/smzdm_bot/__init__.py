"""SMZDM Bot - 什么值得买每日签到 (青龙面板版)。"""

from smzdm_bot.client import SmzdmClient
from smzdm_bot.config import NotifyConfig, Settings, UserConfig, get_settings
from smzdm_bot.exceptions import APIError, ConfigurationError, SmzdmError
from smzdm_bot.models import CheckinResult, LotteryResult, RewardInfo, TaskResult, VipInfo

__version__ = "1.0.0"
__all__ = [
    "SmzdmClient",
    "Settings",
    "UserConfig",
    "NotifyConfig",
    "get_settings",
    "CheckinResult",
    "VipInfo",
    "RewardInfo",
    "LotteryResult",
    "TaskResult",
    "SmzdmError",
    "APIError",
    "ConfigurationError",
]
