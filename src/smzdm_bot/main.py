"""Main entry point for SMZDM Bot."""

from loguru import logger

from smzdm_bot.client import SmzdmClient
from smzdm_bot.config import Settings, UserConfig, get_settings
from smzdm_bot.models import TaskResult
from smzdm_bot.notify import send_notification
from smzdm_bot.tasks import TaskRunner


def run_user(user: UserConfig) -> TaskResult:
    """Execute all tasks for a single user."""
    try:
        with SmzdmClient(user) as client:
            runner = TaskRunner(client)
            return runner.run_all()
    except Exception as e:
        logger.error(f"User {user.name} failed: {e}")
        return TaskResult(user_id=user.name or "unknown", success=False, error=str(e))


def run_all(settings: Settings | None = None) -> list[TaskResult]:
    """Execute tasks for all users."""
    settings = settings or get_settings()
    users = settings.get_users()

    logger.info(f"Running tasks for {len(users)} user(s)")
    results = [run_user(user) for user in users]

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
    results = run_all()

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
