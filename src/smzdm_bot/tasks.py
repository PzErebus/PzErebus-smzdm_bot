"""SMZDM 任务执行模块。"""

import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any

from loguru import logger

from smzdm_bot.client import SmzdmClient
from smzdm_bot.models import CheckinResult, LotteryResult, RewardInfo, TaskResult, VipInfo


class TaskPriority(Enum):
    """任务优先级。"""

    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class TaskInfo:
    """任务元信息。"""

    name: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    optional: bool = True
    delay: tuple[int, int] = (1, 5)


@dataclass
class TaskRunResult:
    """单个任务执行结果。"""

    name: str
    success: bool
    data: Any = None
    error: str | None = None


class TaskRegistry:
    """任务注册器。"""

    def __init__(self) -> None:
        self._tasks: list[tuple[TaskInfo, Callable]] = []

    def task(
        self,
        name: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        optional: bool = True,
        delay: tuple[int, int] = (1, 5),
    ) -> Callable:
        """任务装饰器。"""
        info = TaskInfo(
            name=name,
            description=description or name,
            priority=priority,
            optional=optional,
            delay=delay,
        )

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(instance: Any, *args: Any, **kwargs: Any) -> Any:
                return func(instance, *args, **kwargs)

            self._tasks.append((info, wrapper))
            return wrapper

        return decorator

    def run_all(self, instance: Any) -> list[TaskRunResult]:
        """按优先级执行所有注册的任务。"""
        sorted_tasks = sorted(self._tasks, key=lambda x: x[0].priority.value)
        results: list[TaskRunResult] = []

        for info, func in sorted_tasks:
            logger.info(f"执行: {info.name}")

            if info.delay[1] > 0:
                time.sleep(random.randint(*info.delay))

            try:
                data = func(instance)
                results.append(TaskRunResult(name=info.name, success=True, data=data))
                logger.success(f"{info.name} 完成")

            except Exception as e:
                error_msg = str(e)
                results.append(TaskRunResult(name=info.name, success=False, error=error_msg))

                if info.optional:
                    logger.warning(f"{info.name} 失败: {error_msg}")
                else:
                    logger.error(f"{info.name} 失败: {error_msg}")
                    break

        return results

    def clear(self) -> None:
        """清空所有注册的任务。"""
        self._tasks.clear()


tasks = TaskRegistry()


class TaskRunner:
    """任务执行器。"""

    VIEW_TASK_TYPES = ("faxian", "haojia", "article", "yuanchuang")
    FOLLOW_EVENT_TYPES = ("interactive.follow.user", "interactive.follow.tag")

    def __init__(self, client: SmzdmClient) -> None:
        self.client = client
        self.user_id = client.user_id

    @tasks.task(name="签到", priority=TaskPriority.HIGH, optional=False)
    def checkin(self) -> CheckinResult:
        """每日签到。"""
        data = self.client.post("/checkin")
        result = CheckinResult(**data.get("data", {}))
        logger.info(f"连续签到 {result.consecutive_days} 天")
        return result

    @tasks.task(name="VIP信息", priority=TaskPriority.HIGH)
    def get_vip_info(self) -> VipInfo:
        """获取 VIP 信息。"""
        data = self.client.post("/vip")
        result = VipInfo(**data.get("data", {}).get("vip", {}))
        logger.info(f"VIP 等级: {result.level}")
        return result

    @tasks.task(name="签到奖励", priority=TaskPriority.NORMAL)
    def get_all_reward(self) -> RewardInfo:
        """获取签到奖励。"""
        try:
            data = self.client.post("/checkin/all_reward")
            gift = data.get("data", {}).get("normal_reward", {}).get("gift", {})
            result = RewardInfo(**gift)
            if result.has_reward:
                logger.info(f"奖励: {result.title or result.content}")
            return result
        except Exception:
            return RewardInfo()

    @tasks.task(name="额外奖励", priority=TaskPriority.NORMAL)
    def claim_extra_reward(self) -> bool:
        """领取连续签到额外奖励。"""
        data = self.client.post("/checkin/show_view_v2")
        for row in data.get("data", {}).get("rows", []):
            if row.get("cell_type") == "18001":
                checkin_data = row.get("cell_data", {}).get("checkin_continue", {})
                if checkin_data.get("continue_checkin_reward_show"):
                    self.client.post("/checkin/extra_reward")
                    logger.info("额外奖励已领取!")
                    return True
        logger.info("无额外奖励")
        return False

    @tasks.task(name="抽奖转盘", priority=TaskPriority.LOW, delay=(2, 5))
    def draw_lottery(self) -> LotteryResult:
        """抽奖转盘。"""
        ts = int(time.time())
        params = {"callback": f"jQuery_{ts}", "active_id": "A6X1veWE2O", "_": ts}

        data = self.client.get_jsonp(
            f"{self.client.WEB_BASE}/user/lottery/jsonp_get_current", params
        )
        if not data or data.get("remain_free_lottery_count", 0) < 1:
            return LotteryResult(success=False, message="没有抽奖机会")

        time.sleep(random.randint(1, 3))
        data = self.client.get_jsonp(f"{self.client.WEB_BASE}/user/lottery/jsonp_draw", params)
        if data:
            return LotteryResult(success=True, message=data.get("error_msg", "抽奖完成"))

        return LotteryResult(success=False, message="抽奖失败")

    @tasks.task(name="幸运屋抽奖", priority=TaskPriority.LOW, delay=(2, 5))
    def draw_crowd(self) -> int:
        """幸运屋免费抽奖。"""
        try:
            html = self.client.get_html(f"{self.client.WEB_BASE}/user/crowd/")
            pattern = r'data-crowd_id="(\d+)"[^>]*>[^<]*<div[^>]*>\s*免费抽奖?\s*</div>\s*<span[^>]*>-0</span>'
            crowd_ids = re.findall(pattern, html, re.I)
        except Exception:
            crowd_ids = []

        if not crowd_ids:
            logger.info("无免费抽奖")
            return 0

        count = 0
        for crowd_id in crowd_ids:
            try:
                referer = f"{self.client.WEB_BASE}/user/crowd/p/{crowd_id}/"
                data = self.client.post_web(
                    f"{self.client.WEB_BASE}/user/crowd/ajax_participate",
                    data={"crowd_id": crowd_id, "sourcePage": referer, "client_type": "android", "price_id": 1},
                    referer=referer,
                )
                if data.get("error_code") == 0:
                    msg = re.sub(r"<[^>]+>", "", data.get("data", {}).get("msg", ""))
                    logger.info(f"幸运屋: {msg}")
                    count += 1
            except Exception as e:
                logger.debug(f"幸运屋抽奖失败: {e}")
            time.sleep(random.randint(3, 8))

        return count

    @tasks.task(name="每日任务", priority=TaskPriority.LOW, delay=(2, 5))
    def run_daily_tasks(self) -> int:
        """执行每日任务。"""
        try:
            data = self.client.post("/task/list_v2")
            rows = data.get("data", {}).get("rows", [])
            if not rows:
                logger.info("无任务活动")
                return 0

            first_row = rows[0]
            if isinstance(first_row, list):
                return 0

            cell_data = first_row.get("cell_data", {})
            activity = cell_data.get("activity_task", {})
            accumulate_list = activity.get("accumulate_list", {})

            if isinstance(accumulate_list, list):
                task_groups = accumulate_list
            else:
                task_groups = accumulate_list.get("task_list_v2", [])

            completed = 0
            for group in task_groups:
                tasks_list = group if isinstance(group, list) else group.get("task_list", [])
                for task in tasks_list:
                    completed += self._process_task(task)

            logger.info(f"完成任务: {completed}")
            return completed

        except Exception as e:
            logger.warning(f"每日任务失败: {e}")
            return 0

    def _process_task(self, task: dict) -> int:
        """处理单个任务，返回完成数量。"""
        if not isinstance(task, dict):
            return 0

        status = int(task.get("task_status", 0))
        task_id = task.get("task_id", "")
        name = task.get("task_name", "")

        redirect = task.get("task_redirect_url", {})
        task_type = redirect.get("link_type", "") if isinstance(redirect, dict) else ""
        event_type = task.get("task_event_type", "")

        if status == 2:
            logger.info(f"执行: {name}")

            if task_type in self.VIEW_TASK_TYPES:
                if self._do_view_task(task):
                    time.sleep(random.randint(3, 8))
                    return 1 if self._claim_task_reward(task_id, name) else 0
            elif event_type in self.FOLLOW_EVENT_TYPES or task_type in ("guanzhu", "lanmu"):
                if self._do_follow_task(task):
                    time.sleep(random.randint(3, 8))
                    return 1 if self._claim_task_reward(task_id, name) else 0
            else:
                logger.debug(f"跳过: {task_type}")

            time.sleep(random.randint(3, 8))

        elif status == 3:
            logger.info(f"领取: {name}")
            if self._claim_task_reward(task_id, name):
                time.sleep(random.randint(3, 8))
                return 1

        return 0

    def _do_view_task(self, task: dict) -> bool:
        """执行浏览任务。"""
        redirect = task.get("task_redirect_url", {})
        redirect = redirect if isinstance(redirect, dict) else {}
        article_id = redirect.get("link_val") or task.get("article_id")
        task_id = task.get("task_id", "")
        channel_id = task.get("channel_id", "1")
        view_seconds = int(task.get("view_seconds", 15))

        if not article_id or article_id == "0":
            return False

        logger.info(f"浏览文章 {article_id}...")
        time.sleep(view_seconds + random.randint(5, 15))

        try:
            self.client.post(
                "/task/event_view_article_sync",
                {"article_id": article_id, "channel_id": channel_id, "task_id": task_id},
            )
            return True
        except Exception:
            return False

    def _do_follow_task(self, task: dict) -> bool:
        """执行关注任务。"""
        redirect = task.get("task_redirect_url", {})
        redirect = redirect if isinstance(redirect, dict) else {}
        link_type = redirect.get("link_type", "")
        link_val = redirect.get("link_val", "")

        if link_type == "guanzhu" or task.get("task_event_type") == "interactive.follow.user":
            user = self._get_random_user()
            if not user:
                return False

            user_id = user.get("smzdm_id", "")
            nickname = user.get("nickname", "")

            if self._follow(user_id, nickname, "user", "follow"):
                time.sleep(random.randint(5, 10))
                self._follow(user_id, nickname, "user", "unfollow")
                return True

        elif link_type == "lanmu" and link_val:
            keyword = redirect.get("link_title", link_val)
            if self._follow(link_val, keyword, "tag", "follow"):
                time.sleep(random.randint(5, 10))
                self._follow(link_val, keyword, "tag", "unfollow")
                return True

        return False

    def _follow(self, keyword_id: str, keyword: str, follow_type: str, action: str) -> bool:
        """关注/取关操作。"""
        try:
            self.client.post(
                f"/dingyue/{action}",
                {"keyword_id": keyword_id, "keyword": keyword, "type": follow_type},
                base=self.client.DINGYUE_API,
            )
            return True
        except Exception:
            return False

    def _get_random_user(self) -> dict | None:
        """获取随机推荐用户。"""
        try:
            data = self.client.post(
                "/tuijian/search_result",
                {"nav_id": 0, "page": 1, "type": "user", "time_code": ""},
                base=self.client.DINGYUE_API,
            )
            users = data.get("data", {}).get("rows", [])
            return random.choice(users) if users else None
        except Exception:
            return None

    def _claim_task_reward(self, task_id: str, name: str) -> bool:
        """领取任务奖励。"""
        try:
            self.client.post("/task/activity_task_receive", {"task_id": task_id})
            logger.success(f"奖励: {name}")
            return True
        except Exception:
            return False

    def run_all(self) -> TaskResult:
        """执行所有注册的任务。"""
        logger.info(f"===== 用户: {self.user_id} =====")

        task_results: list[TaskRunResult] = tasks.run_all(self)

        result = TaskResult(user_id=self.user_id)

        for r in task_results:
            if r.data:
                if isinstance(r.data, CheckinResult):
                    result.checkin = r.data
                elif isinstance(r.data, VipInfo):
                    result.vip_info = r.data
                elif isinstance(r.data, RewardInfo):
                    result.reward = r.data
                elif isinstance(r.data, LotteryResult):
                    result.lottery = r.data

        checkin_result = next((r for r in task_results if r.name == "签到"), None)
        result.success = checkin_result is not None and checkin_result.success

        if not result.success and checkin_result:
            result.error = checkin_result.error

        return result
