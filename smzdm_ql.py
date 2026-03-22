"""
什么值得买自动签到脚本
项目地址: https://github.com/PzErebus/PzErebus-smzdm_bot
0 9 * * * smzdm_ql.py
const $ = new Env("什么值得买签到");
"""

import os
import sys
from pathlib import Path

ql_repo_dir = Path("/ql/data/repo/")
repo_name = "PzErebus_PzErebus-smzdm_bot"
repo_dir = Path(ql_repo_dir, repo_name)


def main():
    # 青龙面板支持: 检查多种可能的环境变量名
    cookie = os.environ.get("SMZDM_COOKIE", "")
    
    # 如果没有设置 SMZDM_COOKIE，尝试从青龙面板变量转换
    if not cookie:
        # 检查是否有未加前缀的变量
        cookie = os.environ.get("ANDROID_COOKIE", "")
        if cookie:
            os.environ["SMZDM_COOKIE"] = cookie
            print("使用 ANDROID_COOKIE 作为 SMZDM_COOKIE")
    else:
        print(f"已设置 SMZDM_COOKIE，长度: {len(cookie)}")
    
    if not cookie:
        print("=" * 50)
        print("错误: 未设置 SMZDM_COOKIE 环境变量")
        print("请在青龙面板环境变量中添加:")
        print("  名称: SMZDM_COOKIE")
        print("  值: 你的Cookie字符串")
        print("=" * 50)
        sys.exit(1)
    
    # 检查 SK
    sk = os.environ.get("SMZDM_SK", "")
    if not sk:
        sk = os.environ.get("SK", "")
        if sk:
            os.environ["SMZDM_SK"] = sk
            print("使用 SK 作为 SMZDM_SK")
    
    print(f"仓库目录: {repo_dir}")
    print(f"目录存在: {repo_dir.exists()}")
    
    if not repo_dir.exists():
        print(f"错误: 仓库目录不存在 {repo_dir}")
        print("请先执行: ql repo https://github.com/PzErebus/PzErebus-smzdm_bot.git")
        sys.exit(1)
    
    # 使用 && 而不是 ; 确保命令链正确执行
    cmd = (
        f"cd {str(repo_dir)} && "
        f"pip3 install --root-user-action=ignore --upgrade pip && "
        f"pip3 install --root-user-action=ignore -e . && "
        f"python3 -m smzdm_bot.cli run"
    )
    print(f"执行命令...")
    
    result = os.system(cmd)
    print(f"命令返回码: {result}")
    sys.exit(result)


if __name__ == "__main__":
    main()
