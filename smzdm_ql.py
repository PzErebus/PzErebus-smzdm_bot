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
  - SMZDM_ENABLE_RISKY: 高风险任务白名单，默认关闭。
      取值: comment(自动发评论) / follow(关注取关) / all(两者)，逗号分隔也可

多账号配置 (JSON格式):
  SMZDM_USERS: '[{"cookie": "...", "sk": "...", "name": "账号1"}, {"cookie": "..."}]'
"""

import os
import random
import re
import sys
import time
from pathlib import Path

REPO_NAME = "PzErebus_PzErebus-smzdm_bot"

# 运行所需第三方依赖（对应 requirements.txt）
REQUIRED_DEPS = ["httpx", "loguru", "pycryptodome", "pydantic", "pydantic-settings"]
# 部分 pip 包名与 import 名不同（如 pycryptodome -> Crypto）
IMPORT_TO_PIP = {"Crypto": "pycryptodome"}


def _extract_module_name(err: ImportError):
    """从 `No module named 'x'` 中取出模块名。"""
    text = str(err)
    match = re.search(r"no module named ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
    return match.group(1) if match else None


def report_missing_dependency(err: ImportError) -> bool:
    """把缺依赖的 ImportError 转成可执行的安装提示。命中返回 True。"""
    module = _extract_module_name(err)
    if not module:
        return False
    pip_name = IMPORT_TO_PIP.get(module, module)
    if pip_name not in REQUIRED_DEPS and module not in REQUIRED_DEPS:
        return False

    print(f"[ERROR] 缺少依赖: {module}（pip 包名: {pip_name}）")
    print("[提示] 装一下即可，两种方式任选其一：")
    print("  1) 青龙面板 → 依赖管理 → Python3 → 新建依赖，依次添加：")
    for dep in REQUIRED_DEPS:
        print(f"       {dep}")
    print("  2) 或进入青龙容器执行：")
    print(f"     pip3 install {' '.join(REQUIRED_DEPS)}")
    print(f"[DEBUG] 原始错误: {err}")
    return True


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
        if not report_missing_dependency(e):
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
