"""
什么值得买自动签到脚本
项目地址: https://github.com/PzErebus/PzErebus-smzdm_bot
0 9 * * * smzdm_ql.py
const $ = new Env("什么值得买签到");
"""

import os
from pathlib import Path

ql_repo_dir = Path("/ql/data/repo/")
repo_name = "PzErebus_PzErebus-smzdm_bot"
repo_dir = Path(ql_repo_dir, repo_name)


def main():
    os.system(
        f"cd {str(repo_dir)}; "
        f"pip3 install -q --root-user-action=ignore --upgrade pip; "
        f"pip3 install -q --root-user-action=ignore -e .; "
        f"smzdm-bot run"
    )


if __name__ == "__main__":
    main()
