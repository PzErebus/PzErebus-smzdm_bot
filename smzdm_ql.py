"""
什么值得买自动签到脚本 - 青龙面板版
项目地址: https://github.com/PzErebus/PzErebus-smzdm_bot

定时规则: 0 9 * * *
环境变量:
  - SMZDM_COOKIE: Cookie字符串 (必填)
  - SMZDM_SK: SK值 (可选)
  - SMZDM_PUSH_PLUS_TOKEN: PushPlus推送Token (可选)
  - SMZDM_SC_KEY: Server酱Key (可选)
  - SMZDM_WECOM_WEBHOOK: 企业微信Webhook (可选)
  - SMZDM_TG_BOT_TOKEN: Telegram Bot Token (可选)
  - SMZDM_TG_USER_ID: Telegram User ID (可选)
  - SMZDM_DELAY_MIN: 随机延迟最小秒数，默认0 (可选)
  - SMZDM_DELAY_MAX: 随机延迟最大秒数，默认3600 (可选)

多账号配置 (JSON格式):
  SMZDM_USERS: '[{"cookie": "...", "sk": "...", "name": "账号1"}, {"cookie": "..."}]'
"""

import os
import random
import sys
import time
from pathlib import Path

REPO_NAME = "PzErebus_PzErebus-smzdm_bot"


def add_src_to_path():
    script_path = Path(__file__).resolve()
    possible_paths = [
        Path("/ql/data/scripts", REPO_NAME, "src"),
        Path("/ql/scripts", REPO_NAME, "src"),
        Path("/ql/data/repo", REPO_NAME, "src"),
        Path("/ql/repo", REPO_NAME, "src"),
        script_path.parent / "src",
        script_path.parent.parent / "src",
    ]
    for src_path in possible_paths:
        if src_path.exists():
            sys.path.insert(0, str(src_path))
            print(f"[INFO] 添加源码路径: {src_path}")
            return True
    print(f"[ERROR] 找不到源码目录")
    return False


def setup_env():
    cookie = os.environ.get("SMZDM_COOKIE", "")
    if not cookie:
        cookie = os.environ.get("ANDROID_COOKIE", "")
        if cookie:
            os.environ["SMZDM_COOKIE"] = cookie
            print("[INFO] 使用 ANDROID_COOKIE 作为 SMZDM_COOKIE")
    
    if not os.environ.get("SMZDM_COOKIE"):
        print("[ERROR] 未设置 SMZDM_COOKIE 环境变量")
        sys.exit(1)
    
    sk = os.environ.get("SMZDM_SK", "")
    if not sk:
        sk = os.environ.get("SK", "")
        if sk:
            os.environ["SMZDM_SK"] = sk
            print("[INFO] 使用 SK 作为 SMZDM_SK")


def random_delay():
    """随机延迟启动，避免固定时间执行被识别。
    
    支持的环境变量：
    - SMZDM_DELAY_MIN: 最小延迟秒数（默认 0）
    - SMZDM_DELAY_MAX: 最大延迟秒数（默认 3600，即 1 小时）
    
    示例：
    - 延迟 0-30 分钟：SMZDM_DELAY_MIN=0, SMZDM_DELAY_MAX=1800
    - 延迟 1-2 小时：SMZDM_DELAY_MIN=3600, SMZDM_DELAY_MAX=7200
    - 不延迟：SMZDM_DELAY_MAX=0
    """
    delay_min = int(os.environ.get("SMZDM_DELAY_MIN", 0))
    delay_max = int(os.environ.get("SMZDM_DELAY_MAX", 3600))
    
    if delay_max <= 0:
        return
    
    delay = random.randint(delay_min, delay_max)
    print(f"[INFO] 延时启动，等待 {delay} 秒 ({delay//60} 分 {delay%60} 秒)...")
    time.sleep(delay)


def main():
    print("[INFO] 开始执行 SMZDM 签到脚本")
    
    if not add_src_to_path():
        sys.exit(1)
    
    setup_env()
    random_delay()
    
    try:
        from smzdm_bot.main import main as bot_main
        print("[INFO] 成功导入 smzdm_bot 模块")
        sys.exit(bot_main())
    except ImportError as e:
        print(f"[ERROR] 导入模块失败: {e}")
        print(f"[DEBUG] sys.path: {sys.path}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
