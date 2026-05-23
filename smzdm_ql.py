"""
什么值得买自动签到脚本 - 青龙面板版
"""

import os
import sys
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

def main():
    print("[INFO] 开始执行 SMZDM 签到脚本")
    
    if not add_src_to_path():
        sys.exit(1)
    
    setup_env()
    
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
