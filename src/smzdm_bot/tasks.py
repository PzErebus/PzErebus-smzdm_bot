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

    # 高风险任务（可能触发风控/人工审核），默认一律关闭
    RISKY_FOLLOW = "follow"
    RISKY_COMMENT = "comment"

    # 抽奖兜底活动 ID（正常会以接口返回的 active_id 为准）
    DEFAULT_ACTIVE_ID = "A6X1veWE2O"
    # 中奖结果可能的字段名
    LOTTERY_PRIZE_KEYS = ("prize_name", "prize", "award_name", "prize_title", "win_prize")

    def __init__(self, client: SmzdmClient, risky: set[str] | None = None) -> None:
        self.client = client
        self.user_id = client.user_id
        # 允许执行的高风险任务集合，空集合=全部关闭
        self.risky: set[str] = risky or set()

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
        """抽奖转盘。

        active_id 以前是写死的，活动换期后就会一直抽错；这里改为以接口
        返回的 active_id 为准（仅在接口没给时才用兜底值），并解析中奖结果。
        """
        ts = int(time.time())
        current = self.client.get_jsonp(
            f"{self.client.WEB_BASE}/user/lottery/jsonp_get_current",
            {"callback": f"jQuery_{ts}", "_": ts},
        )
        if not current:
            return LotteryResult(success=False, message="无法获取抽奖信息")

        remain = current.get("remain_free_lottery_count", 0) or 0
        if int(remain) < 1:
            return LotteryResult(success=False, message="没有抽奖机会")

        active_id = (
            current.get("active_id")
            or current.get("activity_id")
            or current.get("activeId")
            or self.DEFAULT_ACTIVE_ID
        )

        time.sleep(random.randint(1, 3))
        data = self.client.get_jsonp(
            f"{self.client.WEB_BASE}/user/lottery/jsonp_draw",
            {"callback": f"jQuery_{int(time.time())}", "active_id": active_id},
        )
        if not data:
            return LotteryResult(success=False, message="抽奖失败（无响应）")

        message = data.get("error_msg") or data.get("msg") or ""
        if not message:
            message = next(
                (str(data[key]) for key in self.LOTTERY_PRIZE_KEYS if data.get(key)),
                "抽奖完成",
            )
        return LotteryResult(success=True, message=str(message))

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

    # 兼容常见的任务分组字段名
    GROUP_KEYS = ("task_list_v2", "task_list", "tasks", "task_list_v1")

    @tasks.task(name="每日任务", priority=TaskPriority.LOW, delay=(2, 5))
    def run_daily_tasks(self) -> int:
        """执行每日任务。

        健壮版：遍历所有活动行（不再只看 rows[0]），兼容 list / dict 多种
        嵌套结构；解析不到或执行失败都会打 warning，避免"静默空转"。
        """
        try:
            data = self.client.post("/task/list_v2")
        except Exception as e:
            logger.warning(f"每日任务: 接口请求失败 -> {e}")
            return 0

        payload = data.get("data") if isinstance(data, dict) else None
        if not isinstance(payload, dict):
            logger.warning(f"每日任务: 接口返回格式异常 -> {str(data)[:200]}")
            return 0

        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            logger.warning("每日任务: 接口未返回任何活动（可能活动已下线或接口变更）")
            return 0

        task_groups = self._extract_task_groups(rows)
        if not task_groups:
            logger.warning(
                f"每日任务: 在 {len(rows)} 个活动中未解析到任务分组，接口结构可能已变更"
            )
            return 0

        completed = failed = 0
        for group in task_groups:
            for task in self._iter_tasks(group):
                try:
                    completed += self._process_task(task)
                except Exception as e:
                    failed += 1
                    logger.warning(
                        f"每日任务: [{task.get('task_name', '?')}] 处理异常 -> {e}"
                    )

        logger.info(f"完成任务: {completed}（异常 {failed}）")
        if completed == 0:
            logger.warning("每日任务: 本轮无任务完成（多为活动未开始或已全部领完）")
        return completed

    def _is_risky_allowed(self, kind: str) -> bool:
        """判断某类高风险任务是否允许执行。"""
        return kind in self.risky

    def _iter_tasks(self, group) -> list:
        """从任务分组中取出任务字典列表。

        分组可能是：任务数组(list of dict) / {"task_list": [...]} /
        本身就是任务对象({"task_id": ...})。
        """
        if isinstance(group, list):
            return [t for t in group if isinstance(t, dict)]
        if isinstance(group, dict):
            for key in self.GROUP_KEYS:
                value = group.get(key)
                if isinstance(value, list):
                    return [t for t in value if isinstance(t, dict)]
            if "task_id" in group:
                return [group]
        return []

    def _extract_task_groups(self, rows: list) -> list:
        """从 /task/list_v2 返回值中抽取所有任务分组（兼容多种嵌套结构）。"""
        groups: list = []

        def _extend(raw):
            if isinstance(raw, list):
                groups.extend([g for g in raw if isinstance(g, (list, dict))])

        for row in rows:
            # 行本身就是 list 结构（[cell, cell, ...]）
            if isinstance(row, list):
                _extend(row)
                continue
            if not isinstance(row, dict):
                continue

            cell_data = row.get("cell_data")
            cell_data = cell_data if isinstance(cell_data, dict) else row

            # 收集所有候选容器：cell_data 本身 + 其下所有子容器。
            # 既兼容已知的 activity_task，也能在接口改名时兜底命中。
            seen_ids = set()
            containers = []
            for cand in [cell_data, *[v for v in cell_data.values() if isinstance(v, dict)]]:
                if id(cand) not in seen_ids:
                    seen_ids.add(id(cand))
                    containers.append(cand)

            for container in containers:
                accumulate_list = container.get("accumulate_list")
                if isinstance(accumulate_list, list):
                    _extend(accumulate_list)
                elif isinstance(accumulate_list, dict):
                    matched = False
                    for key in self.GROUP_KEYS:
                        value = accumulate_list.get(key)
                        if isinstance(value, list):
                            _extend(value)
                            matched = True
                            break
                    # 兜底：字段名未知时，扫描其下所有值找任务数组
                    if not matched:
                        for value in accumulate_list.values():
                            _extend(value)
                # 兼容容器下直接挂任务列表的情况
                for key in self.GROUP_KEYS:
                    value = container.get(key)
                    if isinstance(value, list):
                        _extend(value)

        # 去重：同一分组对象可能被多条路径引用到
        unique: list = []
        seen = set()
        for g in groups:
            if id(g) not in seen:
                seen.add(id(g))
                unique.append(g)
        return unique

    @staticmethod
    def _is_api_success(payload) -> bool:
        """判断接口返回是否成功。

        兼容两种成功标志字段：部分余额接口用 `code`，另一些用 `error_code`，
        两个都没有时视为成功（交由后续字段提取兜底）。
        """
        if not isinstance(payload, dict):
            return False
        for key in ("error_code", "code"):
            value = payload.get(key)
            if value is None:
                continue
            try:
                if int(value) != 0:
                    return False
            except (TypeError, ValueError):
                continue
        return True

    @tasks.task(name="积分余额", priority=TaskPriority.NORMAL, delay=(1, 3))
    def get_points_balance(self) -> PointsBalance:
        """获取积分余额。"""
        try:
            data = {}
            
            apis_to_try = [
                ("/user/points", "data"),
                ("/points", "data"),
                ("/user/home", "data"),
                ("/vip", "data.user_info"),
            ]
            
            for api, path in apis_to_try:
                try:
                    result = self.client.post(api)
                    # 余额接口的成功标志字段不统一：有的返回 code，有的返回 error_code。
                    # 只认其中一种会导致余额永远取不到（碎银一直是 0）。
                    if not self._is_api_success(result):
                        continue
                    parts = path.split(".")
                    current = result
                    for part in parts:
                        current = current.get(part, {})
                    if isinstance(current, dict) and (
                        current.get("gold") or
                        current.get("points") or
                        current.get("coins") or
                        current.get("egold") or
                        current.get("ecoin")
                    ):
                        data = current
                        logger.debug(f"从 {api} 获取余额成功")
                        break
                except Exception as e:
                    logger.debug(f"从 {api} 获取余额失败: {e}")
                    continue
            
            result = PointsBalance(
                gold=data.get("gold", 0) or data.get("egold", 0) or data.get("smzdm_gold", 0) or 0,
                points=data.get("points", 0) or data.get("epoint", 0) or data.get("smzdm_point", 0) or 0,
                coins=data.get("coins", 0) or data.get("ecoin", 0) or data.get("smzdm_coin", 0) or 0,
            )
            
            logger.info(f"💰 金币: {result.gold} | 💎 积分: {result.points} | 🪙 碎银: {result.coins}")
            return result
        except Exception as e:
            logger.debug(f"获取积分余额失败: {e}")
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
            try:
                data = self.client.post("/task/points_task_list")
                task_list = data.get("data", {}).get("task_list", [])
            except Exception:
                try:
                    data = self.client.post("/task/list_v2")
                    task_list = data.get("data", {}).get("task_list", [])
                except Exception:
                    task_list = []
            
            if not task_list:
                logger.info("无积分任务")
                return 0
            
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

    def _get_recommend_articles(self, min_count: int = 1) -> list[dict]:
        """获取推荐文章列表。"""
        try:
            data = self.client.post("/article/recommend_list", {"page": 1, "limit": max(min_count, 20)})
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
                # 自动发评论容易被风控/人工审核，默认关闭
                if not self._is_risky_allowed(self.RISKY_COMMENT):
                    logger.warning(
                        "跳过高风险任务: 自动评论（如需开启请设 SMZDM_ENABLE_RISKY=comment）"
                    )
                    return False
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
                if not self._is_risky_allowed(self.RISKY_FOLLOW):
                    logger.warning(
                        f"跳过高风险任务: {name}（关注类任务默认关闭，"
                        f"如需开启请设 SMZDM_ENABLE_RISKY=follow）"
                    )
                    return 0
                if self._do_follow_task(task):
                    time.sleep(random.randint(3, 8))
                    return 1 if self._claim_task_reward(task_id, name) else 0
            else:
                # 不认识的类型直接跳过，不再无谓等待（否则一轮下来会白等很久）
                logger.debug(f"跳过未知任务类型: {task_type or status}")
                return 0

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
        except Exception as e:
            logger.warning(f"浏览上报失败: 文章 {article_id} -> {e}")
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
        except Exception as e:
            logger.warning(f"领取奖励失败: {name}({task_id}) -> {e}")
            return False

    def run_all(self) -> TaskResult:
        """执行所有注册的任务。"""
        logger.info(f"===== 用户: {self.user_id} =====")

        task_results: list[TaskRunResult] = tasks.run_all(self)

        result = TaskResult(user_id=self.user_id)

        for r in task_results:
            data = r.data
            if data is None:
                continue

            if isinstance(data, CheckinResult):
                result.checkin = data
            elif isinstance(data, VipInfo):
                result.vip_info = data
            elif isinstance(data, RewardInfo):
                result.reward = data
            elif isinstance(data, LotteryResult):
                result.lottery = data
            elif isinstance(data, PointsBalance):
                result.points_balance = data
            elif isinstance(data, ArticleResult):
                result.articles.append(data.to_message())
            elif isinstance(data, int):
                # 任务型返回值是纯数字，按任务名归属到对应汇总字段
                if r.name == "每日任务":
                    result.daily_tasks += data
                elif r.name == "积分任务":
                    result.points_tasks += data
                elif r.name == "幸运屋抽奖":
                    result.lucky_draws += data

        checkin_result = next((r for r in task_results if r.name == "签到"), None)
        result.success = checkin_result is not None and checkin_result.success

        if not result.success and checkin_result:
            result.error = checkin_result.error

        return result
