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

多账号配置 (JSON格式):
  SMZDM_USERS: '[{"cookie": "...", "sk": "...", "name": "账号1"}, {"cookie": "..."}]'
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_NAME = "PzErebus_PzErebus-smzdm_bot"


def get_repo_dir() -> Path:
    """获取仓库目录路径."""
    possible_paths = [
        Path("/ql/data/repo", REPO_NAME),
        Path("/ql/repo", REPO_NAME),
        Path("/ql/scripts", REPO_NAME),
    ]
    for p in possible_paths:
        if p.exists():
            return p
    raise FileNotFoundError(f"找不到仓库目录，请先添加订阅: ql repo https://github.com/PzErebus/PzErebus-smzdm_bot.git")


def setup_env() -> None:
    """设置环境变量."""
    cookie = os.environ.get("SMZDM_COOKIE", "")
    if not cookie:
        cookie = os.environ.get("ANDROID_COOKIE", "")
        if cookie:
            os.environ["SMZDM_COOKIE"] = cookie
            print("[INFO] 使用 ANDROID_COOKIE 作为 SMZDM_COOKIE")

    if not os.environ.get("SMZDM_COOKIE"):
        print("=" * 50)
        print("[ERROR] 未设置 SMZDM_COOKIE 环境变量")
        print("请在青龙面板环境变量中添加:")
        print("  名称: SMZDM_COOKIE")
        print("  值: 你的Cookie字符串")
        print("=" * 50)
        sys.exit(1)

    sk = os.environ.get("SMZDM_SK", "")
    if not sk:
        sk = os.environ.get("SK", "")
        if sk:
            os.environ["SMZDM_SK"] = sk
            print("[INFO] 使用 SK 作为 SMZDM_SK")


def main() -> None:
    """主函数."""
    setup_env()

    repo_dir = get_repo_dir()
    print(f"[INFO] 仓库目录: {repo_dir}")

    cmd = [
        sys.executable, "-m", "smzdm_bot.main"
    ]

    result = subprocess.run(cmd, cwd=str(repo_dir))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
