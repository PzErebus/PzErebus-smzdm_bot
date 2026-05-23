"""SMZDM 任务执行模块。"""

import random
import re
import time

from loguru import logger

from smzdm_bot.client import SmzdmClient
from smzdm_bot.models import (
    ArticleResult,
    CheckinResult,
    LotteryResult,
    PointsBalance,
    RewardInfo,
    TaskResult,
    VipInfo,
)
from smzdm_bot.task_registry import TaskPriority, TaskRunResult, tasks


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

    @tasks.task(name="积分余额", priority=TaskPriority.NORMAL, delay=(1, 3))
    def get_points_balance(self) -> PointsBalance:
        """获取积分余额。"""
        try:
            data = self.client.post("/user/points")
            data = data.get("data", {})
            result = PointsBalance(
                gold=data.get("gold", 0),
                points=data.get("points", 0),
                coins=data.get("coins", 0),
            )
            logger.info(f"💰 金币: {result.gold} | 💎 积分: {result.points} | 🪙 碎银: {result.coins}")
            return result
        except Exception as e:
            logger.warning(f"获取积分余额失败: {e}")
            return PointsBalance()

    @tasks.task(name="文章点赞", priority=TaskPriority.LOW, delay=(2, 4))
    def like_article(self) -> ArticleResult:
        """文章点赞获取积分。"""
        try:
            articles = self._get_recommend_articles()
            if not articles:
                return ArticleResult(success=False, action="点赞", message="无推荐文章")

            article = random.choice(articles)
            article_id = article.get("article_id", "")
            if not article_id:
                return ArticleResult(success=False, action="点赞", message="无效文章ID")

            self.client.post("/article/like", {"article_id": article_id})
            logger.info(f"👍 点赞文章: {article_id}")
            return ArticleResult(success=True, article_id=article_id, action="点赞", points=1)
        except Exception as e:
            logger.warning(f"文章点赞失败: {e}")
            return ArticleResult(success=False, action="点赞", message=str(e))

    @tasks.task(name="文章收藏", priority=TaskPriority.LOW, delay=(2, 4))
    def collect_article(self) -> ArticleResult:
        """收藏文章获取积分。"""
        try:
            articles = self._get_recommend_articles()
            if not articles:
                return ArticleResult(success=False, action="收藏", message="无推荐文章")

            article = random.choice(articles)
            article_id = article.get("article_id", "")
            if not article_id:
                return ArticleResult(success=False, action="收藏", message="无效文章ID")

            self.client.post("/article/collect", {"article_id": article_id})
            logger.info(f"❤️ 收藏文章: {article_id}")
            return ArticleResult(success=True, article_id=article_id, action="收藏", points=2)
        except Exception as e:
            logger.warning(f"文章收藏失败: {e}")
            return ArticleResult(success=False, action="收藏", message=str(e))

    @tasks.task(name="积分任务", priority=TaskPriority.LOW, delay=(2, 5))
    def run_points_tasks(self) -> int:
        """执行积分任务中心的任务。"""
        try:
            data = self.client.post("/task/points_task_list")
            task_list = data.get("data", {}).get("task_list", [])
            
            completed = 0
            for task in task_list:
                task_id = task.get("task_id", "")
                task_name = task.get("task_name", "")
                status = task.get("task_status", 0)
                points = task.get("task_points", 0)
                
                if status == 1:
                    logger.info(f"已完成: {task_name}")
                    continue
                
                if status == 2:
                    if self._execute_points_task(task):
                        time.sleep(random.randint(3, 6))
                        if self._claim_points_reward(task_id):
                            logger.info(f"✅ 完成任务: {task_name} (+{points}积分)")
                            completed += 1
                
                elif status == 3:
                    if self._claim_points_reward(task_id):
                        logger.info(f"✅ 领取奖励: {task_name} (+{points}积分)")
                        completed += 1

            logger.info(f"积分任务完成: {completed}")
            return completed
        except Exception as e:
            logger.warning(f"积分任务执行失败: {e}")
            return 0

    @tasks.task(name="视频任务", priority=TaskPriority.LOW, delay=(2, 5))
    def run_video_tasks(self) -> int:
        """执行视频观看任务获取碎银。"""
        try:
            videos = self._get_video_list()
            if not videos:
                logger.info("无视频可观看")
                return 0

            completed = 0
            for video in videos[:5]:
                video_id = video.get("video_id", "")
                title = video.get("title", "")[:20]
                
                if not video_id:
                    continue

                logger.info(f"🎬 观看视频: {title}...")
                time.sleep(random.randint(15, 30))
                
                if self._report_video_progress(video_id, duration=30):
                    if self._claim_video_reward(video_id):
                        logger.info(f"✅ 视频观看完成: {title}")
                        completed += 1
                    else:
                        logger.warning(f"❌ 领取视频奖励失败: {title}")
                else:
                    logger.warning(f"❌ 视频观看上报失败: {title}")
                
                time.sleep(random.randint(3, 6))

            logger.info(f"视频任务完成: {completed}")
            return completed
        except Exception as e:
            logger.warning(f"视频任务执行失败: {e}")
            return 0

    def _get_video_list(self) -> list[dict]:
        """获取视频列表。"""
        try:
            data = self.client.post("/video/recommend_list", {"page": 1, "limit": 10})
            return data.get("data", {}).get("rows", [])
        except Exception:
            try:
                data = self.client.post("/article/recommend_list", {"page": 1, "limit": 20})
                articles = data.get("data", {}).get("rows", [])
                return [a for a in articles if a.get("article_type") == "video" or "video" in str(a)]
            except Exception:
                return []

    def _report_video_progress(self, video_id: str, duration: int = 30) -> bool:
        """上报视频观看进度。"""
        try:
            self.client.post(
                "/video/progress_report",
                {"video_id": video_id, "duration": duration, "progress": 100}
            )
            return True
        except Exception:
            try:
                self.client.post(
                    "/task/video_watch",
                    {"video_id": video_id, "watch_time": duration}
                )
                return True
            except Exception:
                return False

    def _claim_video_reward(self, video_id: str) -> bool:
        """领取视频观看奖励。"""
        try:
            self.client.post("/video/claim_reward", {"video_id": video_id})
            return True
        except Exception:
            try:
                self.client.post("/task/video_reward", {"video_id": video_id})
                return True
            except Exception:
                return False

    def _get_recommend_articles(self) -> list[dict]:
        """获取推荐文章列表。"""
        try:
            data = self.client.post("/article/recommend_list", {"page": 1, "limit": 20})
            return data.get("data", {}).get("rows", [])
        except Exception:
            return []

    def _execute_points_task(self, task: dict) -> bool:
        """执行积分任务。"""
        task_type = task.get("task_type", "")
        article_id = task.get("article_id", "")
        
        try:
            if task_type in ("view", "read"):
                if article_id:
                    self.client.post("/task/event_view_article_sync", {"article_id": article_id})
                    time.sleep(random.randint(10, 20))
                    return True
            
            elif task_type == "share":
                if article_id:
                    self.client.post("/task/share_article", {"article_id": article_id})
                    return True
            
            elif task_type == "comment":
                if article_id:
                    comments = ["不错", "很好", "支持", "点赞", "收藏了"]
                    comment = random.choice(comments)
                    self.client.post("/comment/add", {"article_id": article_id, "content": comment})
                    return True
            
            elif task_type in ("follow", "attention"):
                user_id = task.get("user_id", "")
                if user_id:
                    self.client.post("/dingyue/follow", {"keyword_id": user_id, "keyword": "", "type": "user"}, base=self.client.DINGYUE_API)
                    return True
        except Exception as e:
            logger.debug(f"执行积分任务失败: {e}")
        
        return False

    def _claim_points_reward(self, task_id: str) -> bool:
        """领取积分任务奖励。"""
        try:
            self.client.post("/task/points_task_receive", {"task_id": task_id})
            return True
        except Exception:
            return False

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
                elif isinstance(r.data, PointsBalance):
                    result.points_balance = r.data

        checkin_result = next((r for r in task_results if r.name == "签到"), None)
        result.success = checkin_result is not None and checkin_result.success

        if not result.success and checkin_result:
            result.error = checkin_result.error

        return result
