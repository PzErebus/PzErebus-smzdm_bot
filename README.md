# 什么值得买每日签到脚本

<p>
    <img src="https://img.shields.io/github/actions/workflow/status/Chasing66/smzdm_bot/checkin.yml?label=CheckIn">
    <img src="https://img.shields.io/github/actions/workflow/status/Chasing66/smzdm_bot/build.yml?label=Build">
    <img src="https://img.shields.io/github/license/Chasing66/smzdm_bot">
    <img src="https://img.shields.io/docker/pulls/enwaiax/smzdm_bot">
</p>

## 更新日志

- 2024-xx-xx, 重构项目，使用 src layout 和 uv 管理依赖
- 2023-04-23，更新抽奖功能
- 2023-04-06, 新增企业微信BOT-WEBHOOK通知推送方式，仅需要`ANDROID_COOKIE`一个变量, `SK`改为可选变量
- 2023-03-02, 新增每日抽奖
- 2023-03-01, 支持青龙面板且支持多账号
- 2023-02-25, 新增`all_reward` 和`extra_reward`两个接口，本地支持多用户运行
- 2023-02-18, 通过安卓端验证登录

## 1. 实现功能

- 每日签到, 额外奖励，随机奖励
- 多种运行方式: GitHub Action, 本地运行，docker， 青龙面板
- 多种通知方式: `pushplus`, `server酱`,`企业微信bot-webhook`, `telegram bot`
- 支持多账号(需配置`config.toml`)

## 2. 项目结构

```
smzdm_bot/
├── src/
│   └── smzdm_bot/
│       ├── __init__.py
│       ├── cli.py           # 命令行入口
│       ├── main.py          # 主逻辑
│       ├── scheduler.py     # 定时任务
│       ├── config/
│       │   └── config_example.toml
│       ├── notify/
│       │   └── notify.py    # 通知模块
│       └── utils/
│           ├── file_helper.py
│           ├── smzdm_bot.py
│           └── smzdm_tasks.py
├── pyproject.toml           # 项目配置 (uv/pip)
├── Dockerfile
├── docker-compose.yml
└── smzdm_ql.py             # 青龙面板脚本
```

## 3. 配置

支持两种读取配置的方法，从`环境变量`或者`config.toml`中读取

### 3.1 从环境变量中读取配置

```conf
# Cookie
ANDROID_COOKIE = ""
SK = "" # 可选，如果抓包抓到最好设置

# Notification
PUSH_PLUS_TOKEN = ""
SC_KEY = ""
WECOM_BOT_WEBHOOK = ""
TG_BOT_TOKEN = ""
TG_USER_ID = ""

# 用于自定义反代的Telegram Bot API(按需设置)
TG_BOT_API = ""

# 用于docker运行的定时设定(可选)，未设定则随机定时执行
SCH_HOUR=
SCH_MINUTE=
```

### 3.2 从`config.toml`中读取

参考模板 [src/smzdm_bot/config/config_example.toml](https://github.com/Chasing66/smzdm_bot/blob/main/src/smzdm_bot/config/config_example.toml)

```toml
[user.A]
ANDROID_COOKIE = ""
SK = "" # 可选，如果抓包抓到最好设置

[user.B]
# Disable userB的签到. 不配置此参数默认启用该用户
Disable = true
ANDROID_COOKIE = ""
SK = "" # 可选，如果抓包抓到最好设置

[notify]
PUSH_PLUS_TOKEN = ""
SC_KEY = ""
WECOM_BOT_WEBHOOK = ""
TG_BOT_TOKEN = ""
TG_USER_ID = ""
TG_BOT_API = ""
```

## 4. 使用

### 4.1 青龙面板

```
ql repo https://github.com/Chasing66/smzdm_bot.git "smzdm_ql.py"
```

默认情况下从环境变量读取配置,仅支持单用户.

如果需要支持多用户，推荐使用`config.toml`, 配置参考 [3.2 从`config.toml`中读取](#32-从configtoml中读取).
配置完成后, 拷贝`config.toml`到青龙容器内的`/ql/data/repo/Chasing66_smzdm_bot/src/smzdm_bot/config`

```
docker cp config.toml <你的青龙容器名称>:/ql/data/repo/Chasing66_smzdm_bot/src/smzdm_bot/config
```

### 4.2 本地直接运行 (推荐使用 uv)

克隆本项目到本地, 按照需求配置

**使用 uv (推荐)**

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆并安装
git clone https://github.com/Chasing66/smzdm_bot.git
cd smzdm_bot
uv sync

# 配置
cp src/smzdm_bot/config/config_example.toml src/smzdm_bot/config/config.toml
# 编辑 config.toml 填入你的配置

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
source .venv/bin/activate
pip install -e .

# 配置
cp src/smzdm_bot/config/config_example.toml src/smzdm_bot/config/config.toml
# 编辑 config.toml

# 运行
smzdm-bot
```

### 4.3 本地 docker-compose 运行

配置参考 [3.2 从`config.toml`中读取](#32-从configtoml中读取)

**使用环境变量**

创建 `.env` 文件:

```env
ANDROID_COOKIE=your_cookie_here
SK=your_sk_here
PUSH_PLUS_TOKEN=your_token
```

运行:

```bash
docker-compose up -d
```

**使用 config.toml**

修改 `docker-compose.yml`, 取消 volumes 注释:

```yaml
services:
  smzdm_bot:
    image: enwaiax/smzdm_bot
    container_name: smzdm_bot
    restart: on-failure
    volumes:
      - ./config.toml:/smzdm_bot/config/config.toml
```

### 4.4 GitHub Action 运行

> GitHub Action 禁止对于 Action 资源的滥用，请尽可能使用其他方式

GitHub Action 仅支持`env`配置方式, **务必自行更改为随机时间**

1. Fork[此仓库项目](https://github.com/Chasing66/smzdm_bot)>, 欢迎`star`~
2. 修改 `.github/workflows/checkin.yml`里的下面部分, 取消`schedule`两行的注释，自行设定时间

```yaml
# UTC时间，对应Beijing时间 9：30
schedule:
  - cron: "30 1 * * *"
```

3. 在仓库 Settings -> Secrets 中添加环境变量

## 5. 其它

### 5.1 手机抓包

> 抓包有一定门槛，请自行尝试! 如果实在解决不了，请我喝瓶可乐可以帮忙

抓包工具可使用 HttpCanary，教程参考[HttpCanary 抓包](https://juejin.cn/post/7177682063699968061)

1. 按照上述教程配置好 HttpCanary
2. 开始抓包，并打开什么值得买 APP
3. 过滤`https://user-api.smzdm.com/checkin`的`post`请求并查看
4. 点击右上角分享，分享 cURL，复制保存该命令
5. 将复制的 curl 命令转换为 python 格式，[方法](https://curlconverter.com/)
6. 填入转换后的`Cookies`和`sk`. `Cookies`在`headers`里，`sk`在`data`里, `sk`是可选项

## 6. Stargazers over time

[![Stargazers over time](https://starchart.cc/Chasing66/smzdm_bot.svg)](https://starchart.cc/Chasing66/smzdm_bot)
