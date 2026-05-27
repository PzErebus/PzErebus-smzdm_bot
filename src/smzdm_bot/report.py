"""执行报告生成器。"""

import time
from datetime import datetime
from typing import List, Optional, Tuple

from loguru import logger

from smzdm_bot.config import Settings
from smzdm_bot.models import TaskResult
from smzdm_bot.task_registry import TaskPriority, TaskRunResult


class ExecutionReporter:
    """执行报告生成器。"""

    @staticmethod
    def generate_summary_report(
        results: List[TaskResult],
        settings: Settings,
        start_time: float,
    ) -> str:
        """生成汇总报告。

        Args:
            results: 用户任务结果列表
            settings: 配置
            start_time: 执行开始时间戳

        Returns:
            美化的报告字符串
        """
        end_time = time.time()
        total_duration = int(end_time - start_time)

        lines = [
            "",
            "╔════════════════════════════════════════════════════════════════╗",
            "║                   🎉 什么值得买签到执行报告                    ║",
            "╚════════════════════════════════════════════════════════════════╝",
            "",
        ]

        # 基本信息
        lines.extend(ExecutionReporter._generate_basic_info(total_duration))

        # 每个用户的详细情况
        for result in results:
            lines.extend(ExecutionReporter._generate_user_report(result))

        # 执行统计
        lines.extend(ExecutionReporter._generate_stats(results))

        # 通知配置
        lines.extend(ExecutionReporter._generate_notify_summary(settings))

        lines.extend([
            "",
            "╔════════════════════════════════════════════════════════════════╗",
            "║                        ✨ 今日成果                              ║",
            "╚════════════════════════════════════════════════════════════════╝",
        ])

        # 收集成就
        for result in results:
            if result.checkin:
                lines.append(f"    🎊 连续签到: {result.checkin.consecutive_days} 天 🔥")
            if result.vip_info:
                lines.append(f"    👑 VIP 等级: {result.vip_info.level} 🏆")
        lines.append(f"    ✅ 所有任务执行成功 🎉")

        lines.extend([
            "",
            "─" * 64,
            f"由 PzErebus-smzdm_bot 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ])

        return "\n".join(lines)

    @staticmethod
    def _generate_basic_info(total_duration: int) -> List[str]:
        """生成基本信息部分。"""
        now = datetime.now()
        return [
            "📋 基本信息",
            "─" * 64,
            f"  执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  执行时长: {total_duration} 秒",
            "",
        ]

    @staticmethod
    def _generate_user_report(result: TaskResult) -> List[str]:
        """生成单个用户的报告。"""
        lines = [
            f"👤 用户: {result.user_id}",
            "─" * 64,
        ]

        # 签到信息
        if result.checkin:
            lines.append(f"  🎯 签到: ✅ 成功 | 连续 {result.checkin.consecutive_days} 天")

        # VIP信息
        if result.vip_info:
            lines.append(f"  👑 VIP: 等级 {result.vip_info.level}")

        # 积分余额
        if result.points_balance:
            lines.append(
                f"  💴 余额: 💰 {result.points_balance.gold} 金币 | "
                f"💎 {result.points_balance.points} 积分 | "
                f"🪙 {result.points_balance.coins} 碎银"
            )

        # 签到奖励
        if result.reward and result.reward.has_reward:
            lines.append(f"  🎁 奖励: {result.reward.title or result.reward.content}")

        # 抽奖结果
        if result.lottery:
            lines.append(f"  🎰 抽奖: {result.lottery.message}")

        if result.error:
            lines.append(f"  ❌ 错误: {result.error}")

        lines.append("")
        return lines

    @staticmethod
    def _generate_stats(results: List[TaskResult]) -> List[str]:
        """生成执行统计。"""
        total = len(results)
        success = sum(1 for r in results if r.success)
        failed = total - success

        return [
            "📊 执行统计",
            "─" * 64,
            f"  总用户数: {total}",
            f"  成功数: {success} ✅",
            f"  失败数: {failed} ❌",
            f"  成功率: {(success/total*100):.1f}%",
            "",
        ]

    @staticmethod
    def _generate_notify_summary(settings: Settings) -> List[str]:
        """生成通知配置摘要。"""
        notify = settings.get_notify_config()
        return [
            "📢 通知推送",
            "─" * 64,
            f"  PushPlus: {'✅ 已配置' if notify.push_plus_token else '❌ 未配置'}",
            f"  ServerChan: {'✅ 已配置' if notify.sc_key else '❌ 未配置'}",
            f"  企业微信: {'✅ 已配置' if notify.wecom_webhook else '❌ 未配置'}",
            f"  Telegram: {'✅ 已配置' if (notify.tg_bot_token and notify.tg_user_id) else '❌ 未配置'}",
            f"  可用渠道: {'是' if notify.has_any_provider else '否'}",
            "",
        ]


def print_report(results: List[TaskResult], settings: Settings, start_time: float) -> None:
    """打印美化的执行报告。"""
    report = ExecutionReporter.generate_summary_report(results, settings, start_time)
    logger.info("\n" + report)
