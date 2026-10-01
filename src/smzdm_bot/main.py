"""Main entry point for SMZDM Bot."""

import random
import time

from loguru import logger

from smzdm_bot.client import SmzdmClient
from smzdm_bot.config import Settings, UserConfig, get_settings
from smzdm_bot.models import TaskResult
from smzdm_bot.notify import send_notification
from smzdm_bot.report import print_report
from smzdm_bot.tasks import TaskRunner

# 多账号之间的随机间隔（秒）
USER_GAP_MIN = 15
USER_GAP_MAX = 45

# SMZDM_ENABLE_RISKY 的取值别名（默认不在表中 => 不开启任何高风险任务）
RISKY_ALIASES = {
    "all": {"comment", "follow"},
    "全部": {"comment", "follow"},
    "*": {"comment", "follow"},
    "true": {"comment", "follow"},
    "1": {"comment", "follow"},
    "comment": {"comment"},
    "评论": {"comment"},
    "follow": {"follow"},
    "关注": {"follow"},
}


def parse_risky_tasks(setting: str) -> set[str]:
    """解析高风险任务白名单。

    未配置或配置无法识别时返回空集合（高风险任务全部关闭）。
    """
    enabled: set[str] = set()
    for item in (setting or "").replace("|", ",").split(","):
        enabled |= RISKY_ALIASES.get(item.strip().lower(), set())
    return enabled


def run_user(user: UserConfig, risky: set[str] | None = None) -> TaskResult:
    """Execute all tasks for a single user."""
    try:
        with SmzdmClient(user) as client:
            runner = TaskRunner(client, risky=risky)
            return runner.run_all()
    except Exception as e:
        logger.error(f"User {user.name} failed: {e}")
        return TaskResult(user_id=user.name or "unknown", success=False, error=str(e))


def run_all(settings: Settings | None = None) -> list[TaskResult]:
    """Execute tasks for all users."""
    settings = settings or get_settings()
    users = settings.get_users()

    logger.info(f"Running tasks for {len(users)} user(s)")

    risky = parse_risky_tasks(settings.enable_risky)
    if risky:
        logger.info(f"已开启高风险任务: {', '.join(sorted(risky))}")
    else:
        logger.info("高风险任务（自动评论/关注取关）默认关闭，"
                    "需要时设 SMZDM_ENABLE_RISKY=comment 或 follow 开启")

    results: list[TaskResult] = []
    for index, user in enumerate(users):
        # 账号之间留一段随机间隔，避免同一 IP 连续高频请求被风控命中
        if index > 0:
            gap = random.randint(USER_GAP_MIN, USER_GAP_MAX)
            logger.info(f"等待 {gap} 秒后处理下一个账号（{index + 1}/{len(users)}）...")
            time.sleep(gap)
        results.append(run_user(user, risky=risky))

    notify = settings.get_notify_config()
    logger.info(f"通知配置 - PushPlus: {'已配置' if notify.push_plus_token else '未配置'}")
    logger.info(f"通知配置 - ServerChan: {'已配置' if notify.sc_key else '未配置'}")
    logger.info(f"通知配置 - 企业微信: {'已配置' if notify.wecom_webhook else '未配置'}")
    logger.info(f"通知配置 - Telegram: {'已配置' if (notify.tg_bot_token and notify.tg_user_id) else '未配置'}")
    logger.info(f"是否有可用通知渠道: {notify.has_any_provider}")

    if notify.has_any_provider and results:
        ok = sum(1 for r in results if r.success)
        logger.info(f"发送通知: {ok}/{len(results)}")
        send_notification(
            notify,
            title=f"SMZDM ({ok}/{len(results)})",
            content="\n\n".join(r.to_message() for r in results),
        )
    elif not notify.has_any_provider:
        logger.info("未配置任何通知渠道，跳过推送")

    return results


def main() -> int:
    """Entry point for青龙面板."""
    start_time = time.time()
    settings = get_settings()
    
    results = run_all(settings)

    # 打印美化报告
    print_report(results, settings, start_time)

    if not results:
        logger.warning("No users configured")
        return 1

    failed = sum(1 for r in results if not r.success)
    if failed:
        logger.warning(f"{failed} user(s) failed")
        return 1

    logger.success("All done!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
