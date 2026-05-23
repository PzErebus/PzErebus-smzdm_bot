# 什么值得买每日签到脚本 (青龙面板版)

<p>
    <img src="https://img.shields.io/github/license/PzErebus/PzErebus-smzdm_bot">
</p>

## 更新日志

- 2026-05-23, 优化青龙面板启动脚本，修复模块导入问题
- 2026-03-21, 更新 APP 版本至 11.1.63，修复每日任务 API 格式变化
- 2023-04-23，更新抽奖功能
- 2023-04-06, 新增企业微信BOT-WEBHOOK通知推送方式
- 2023-03-02, 新增每日抽奖
- 2023-03-01, 支持青龙面板且支持多账号
- 2023-02-18, 通过安卓端验证登录

## 功能

- 每日签到, 额外奖励，随机奖励
- VIP 信息查询
- 抽奖转盘、幸运屋抽奖
- 每日任务自动执行
- 多种通知方式: `pushplus`, `server酱`, `企业微信bot-webhook`, `telegram bot`
- 支持多账号

## 使用方法

### 1. 添加订阅

在青龙面板「订阅管理」中添加：

```
名称: smzdm_bot
链接: https://github.com/PzErebus/PzErebus-smzdm_bot.git
定时: 0 9 * * *
```

或使用命令：

```
ql repo https://github.com/PzErebus/PzErebus-smzdm_bot.git "smzdm_ql.py"
```

### 2. 安装依赖

在青龙面板「依赖管理」→「Python3」中添加：

```
httpx
loguru
pycryptodome
pydantic
pydantic-settings
```

### 3. 配置环境变量

在青龙面板「环境变量」中添加：

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `SMZDM_COOKIE` | Cookie字符串 | ✅ |
| `SMZDM_SK` | SK值 | ❌ |
| `SMZDM_PUSH_PLUS_TOKEN` | PushPlus推送Token | ❌ |
| `SMZDM_SC_KEY` | Server酱Key | ❌ |
| `SMZDM_WECOM_WEBHOOK` | 企业微信Webhook | ❌ |
| `SMZDM_TG_BOT_TOKEN` | Telegram Bot Token | ❌ |
| `SMZDM_TG_USER_ID` | Telegram User ID | ❌ |

### 4. 多账号配置

使用 JSON 格式配置多账号：

```
变量名: SMZDM_USERS
值: [{"cookie": "账号1的cookie", "sk": "账号1的sk", "name": "账号1"}, {"cookie": "账号2的cookie"}]
```

## 获取 Cookie

> 抓包有一定门槛，请自行尝试!

1. 使用 HttpCanary 等抓包工具
2. 打开什么值得买 APP
3. 过滤 `https://user-api.smzdm.com/checkin` 的 POST 请求
4. 提取请求头中的 `Cookie` 和请求体中的 `sk`

## 项目结构

```
smzdm_bot/
├── src/smzdm_bot/
│   ├── __init__.py      # 模块导出
│   ├── client.py        # HTTP 客户端、签名和异常定义
│   ├── main.py          # 主入口
│   ├── models.py        # 数据模型
│   ├── notify.py        # 通知模块
│   ├── tasks.py         # 任务执行和任务注册器
│   └── config/
│       └── __init__.py  # 配置管理
├── smzdm_ql.py          # 青龙面板入口
├── requirements.txt     # 依赖列表
└── pyproject.toml       # 项目配置
```
