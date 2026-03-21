# 什么值得买每日签到脚本

<p>
    <img src="https://img.shields.io/github/actions/workflow/status/Chasing66/smzdm_bot/checkin.yml?label=CheckIn">
    <img src="https://img.shields.io/github/actions/workflow/status/Chasing66/smzdm_bot/build.yml?label=Build">
    <img src="https://img.shields.io/github/license/Chasing66/smzdm_bot">
    <img src="https://img.shields.io/docker/pulls/enwaiax/smzdm_bot">
</p>

## 更新日志

- 2026-03-21, 更新 APP 版本至 11.1.63，修复每日任务 API 格式变化
- 2024-xx-xx, 重构项目，使用 src layout 和 uv 管理依赖
- 2023-04-23，更新抽奖功能
- 2023-04-06, 新增企业微信BOT-WEBHOOK通知推送方式，仅需要`ANDROID_COOKIE`一个变量, `SK`改为可选变量
- 2023-03-02, 新增每日抽奖
- 2023-03-01, 支持青龙面板且支持多账号
- 2023-02-25, 新增`all_reward` 和`extra_reward`两个接口，本地支持多用户运行
- 2023-02-18, 通过安卓端验证登录

## 1. 实现功能

- 每日签到, 额外奖励，随机奖励
- VIP 信息查询
- 抽奖转盘、幸运屋抽奖
- 每日任务自动执行
- 多种运行方式: GitHub Action, 本地运行，docker， 青龙面板
- 多种通知方式: `pushplus`, `server酱`,`企业微信bot-webhook`, `telegram bot`
- 支持多账号

## 2. 项目结构

```
smzdm_bot/
├── src/
│   └── smzdm_bot/
│       ├── __init__.py
│       ├── cli.py           # 命令行入口
│       ├── client.py        # HTTP 客户端和签名
│       ├── main.py          # 主逻辑
│       ├── models.py        # 数据模型
│       ├── notify.py        # 通知模块
│       ├── scheduler.py     # 定时任务
│       ├── task_registry.py # 任务注册器
│       ├── tasks.py         # 任务执行
│       ├── exceptions.py    # 异常定义
│       └── config/
│           └── __init__.py  # 配置管理
├── pyproject.toml           # 项目配置 (uv/pip)
├── Dockerfile
├── docker-compose.yml
└── smzdm_ql.py              # 青龙面板脚本
```

## 3. 配置

配置通过环境变量读取，支持 `.env` 文件。

### 3.1 环境变量

```conf
# Cookie (必填)
SMZDM_COOKIE = ""

# SK (可选，如果抓包抓到最好设置)
SMZDM_SK = ""

# 多用户模式 (可选，JSON 数组格式)
SMZDM_USERS = '[{"cookie": "...", "sk": "...", "name": "用户1"}, {"cookie": "..."}]'

# 通知配置 (可选)
SMZDM_PUSH_PLUS_TOKEN = ""      # PushPlus
SMZDM_SC_KEY = ""               # Server酱
SMZDM_WECOM_WEBHOOK = ""        # 企业微信
SMZDM_TG_BOT_TOKEN = ""         # Telegram Bot Token
SMZDM_TG_USER_ID = ""           # Telegram User ID
SMZDM_TG_API_BASE = ""          # Telegram API 反代 (可选)

# 定时任务配置 (可选)
SMZDM_SCH_HOUR = 9              # 执行小时 (0-23)
SMZDM_SCH_MINUTE = 0            # 执行分钟 (0-59)
SMZDM_TIMEZONE = "Asia/Shanghai"
```

### 3.2 使用 .env 文件

在项目根目录创建 `.env` 文件：

```env
SMZDM_COOKIE=你的Cookie
SMZDM_SK=你的SK(可选)
SMZDM_PUSH_PLUS_TOKEN=你的推送Token
```

## 4. 使用

### 4.1 青龙面板

```
ql repo https://github.com/Chasing66/smzdm_bot.git "smzdm_ql.py"
```

在青龙面板中添加环境变量 `SMZDM_COOKIE`。

### 4.2 本地直接运行 (推荐使用 uv)

**使用 uv (推荐)**

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆并安装
git clone https://github.com/Chasing66/smzdm_bot.git
cd smzdm_bot
uv sync

# 创建 .env 文件并配置
echo "SMZDM_COOKIE=你的Cookie" > .env

# 运行一次
uv run smzdm-bot

# 或者运行定时任务
uv run smzdm-scheduler
```

**使用 pip**

```bash
git clone https://github.com/Chasing66/smzdm_bot.git
cd smzdm_bot
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 创建 .env 文件并配置
echo "SMZDM_COOKIE=你的Cookie" > .env

# 运行
smzdm-bot

# 调试模式
smzdm-bot run --debug

# 查看配置
smzdm-bot config
```

### 4.3 本地 docker-compose 运行

创建 `.env` 文件:

```env
SMZDM_COOKIE=你的Cookie
SMZDM_PUSH_PLUS_TOKEN=你的Token
```

运行:

```bash
docker-compose up -d
```

### 4.4 GitHub Action 运行

> GitHub Action 禁止对于 Action 资源的滥用，请尽可能使用其他方式

1. Fork [此仓库项目](https://github.com/Chasing66/smzdm_bot)，欢迎 `star`~
2. 修改 `.github/workflows/checkin.yml` 里的 schedule 时间
3. 在仓库 Settings -> Secrets 中添加环境变量:
   - `SMZDM_COOKIE`: 你的 Cookie

## 5. 命令说明

```bash
# 查看帮助
smzdm-bot --help

# 执行签到
smzdm-bot run

# 调试模式
smzdm-bot run --debug

# 指定日志文件
smzdm-bot run --log-file ./my.log

# 启动定时任务
smzdm-bot schedule

# 查看当前配置
smzdm-bot config

# 查看版本
smzdm-bot --version
```

## 6. 其它

### 6.1 手机抓包

> 抓包有一定门槛，请自行尝试!

抓包工具可使用 HttpCanary，教程参考[HttpCanary 抓包](https://juejin.cn/post/7177682063699968061)

1. 按照上述教程配置好 HttpCanary
2. 开始抓包，并打开什么值得买 APP
3. 过滤`https://user-api.smzdm.com/checkin`的`post`请求并查看
4. 点击右上角分享，分享 cURL，复制保存该命令
5. 将复制的 curl 命令转换为 python 格式，[方法](https://curlconverter.com/)
6. 填入转换后的`Cookies`和`sk`. `Cookies`在`headers`里，`sk`在`data`里, `sk`是可选项

## 7. Stargazers over time

[![Stargazers over time](https://starchart.cc/Chasing66/smzdm_bot.svg)](https://starchart.cc/Chasing66/smzdm_bot)
