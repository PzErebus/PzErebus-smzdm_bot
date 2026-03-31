"""通知模块 - 支持多种推送方式。"""

from typing import Callable

import httpx
from loguru import logger

from smzdm_bot.config import NotifyConfig

TIMEOUT = 30.0


def _send_request(
    name: str,
    url: str,
    payload: dict | None = None,
    data: dict | None = None,
    check_success: Callable[[dict], bool] | None = None,
) -> bool:
    """通用请求发送函数。"""
    try:
        if payload:
            resp = httpx.post(url, json=payload, timeout=TIMEOUT)
        else:
            resp = httpx.post(url, data=data or {}, timeout=TIMEOUT)

        result = resp.json()
        if check_success and check_success(result):
            logger.success(f"✅ {name}: 发送成功")
            return True
        logger.warning(f"{name} 发送失败: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"{name} 发送异常: {e}")
    return False


def send_pushplus(token: str, title: str, content: str) -> bool:
    """PushPlus 推送。"""
    if not token:
        return False
    return _send_request(
        "PushPlus",
        "https://www.pushplus.plus/send",
        payload={"token": token, "title": title, "content": content, "template": "html"},
        check_success=lambda r: r.get("code") == 200,
    )


def send_serverchan(key: str, title: str, content: str) -> bool:
    """Server酱 推送。"""
    if not key:
        return False
    return _send_request(
        "ServerChan",
        f"https://sctapi.ftqq.com/{key}.send",
        data={"title": title, "desp": content},
        check_success=lambda r: r.get("code") == 0,
    )


def send_wecom(webhook: str, title: str, content: str) -> bool:
    """企业微信 Bot 推送。"""
    if not webhook:
        return False
    return _send_request(
        "WeCom",
        webhook,
        payload={"msgtype": "text", "text": {"content": f"{title}\n{content}"}},
        check_success=lambda r: r.get("errcode") == 0,
    )


def send_telegram(
    token: str, chat_id: str, title: str, content: str, api_base: str = ""
) -> bool:
    """Telegram Bot 推送。"""
    if not token or not chat_id:
        return False
    base = api_base.rstrip("/") if api_base else "https://api.telegram.org"
    return _send_request(
        "Telegram",
        f"{base}/bot{token}/sendMessage",
        payload={
            "chat_id": chat_id,
            "text": f"*{title}*\n\n{content}",
            "parse_mode": "Markdown",
        },
        check_success=lambda r: r.get("ok") is True,
    )


def send_notification(config: NotifyConfig, title: str, content: str) -> int:
    """发送通知到所有已配置的渠道。

    Returns:
        成功发送的数量。
    """
    if not config.has_any_provider:
        logger.info("未配置通知渠道")
        return 0

    count = 0

    if config.push_plus_token:
        count += send_pushplus(config.push_plus_token, title, content)

    if config.sc_key:
        count += send_serverchan(config.sc_key, title, content)

    if config.wecom_webhook:
        count += send_wecom(config.wecom_webhook, title, content)

    if config.tg_bot_token and config.tg_user_id:
        count += send_telegram(
            config.tg_bot_token, config.tg_user_id, title, content, config.tg_api_base
        )

    logger.info(f"通知发送完成: {count} 个渠道")
    return count
