# Flavalon

> A place for peace.

Flavalon 是一个自托管的个人日程 / 待办 / 日记应用。它把「今天要做什么」、
「今天写了什么」和「想公开分享的日程」放在同一个安静的页面里。

后端使用 Flask + SQLite，前端是零构建的原生 JS，开箱即用。

## 功能

- **待办事项**：添加、完成、删除，按创建/完成日期归档，自动隐藏往日已完成项。
- **每日小记**：按日期保存 Markdown 笔记，带日历红点标记与实时预览，1 秒防抖自动保存。
- **每日事项**：提交标题 + Markdown 详情，进入审核队列，审核通过后对外发布。
- **数据管理**：一键导出完整 JSON 备份 / 合并 Markdown，支持覆盖导入。
- **主题与天气**：亮暗色主题切换、基于浏览器定位的天气展示。

## 目录结构

```
app/
  __init__.py       应用工厂
  config.py         配置（环境变量）
  db.py             SQLite 连接与建表
  auth.py           匿名用户 Cookie 与管理员会话
  store.py          数据访问层（待办 / 小记 / 日程）
  schema.sql        数据库结构
  bot.py            后台审核机器人
  routes/
    pages.py        页面
    api.py          普通用户 JSON API
    admin.py        管理后台
  templates/        Jinja 模板
  static/           原生 JS / CSS
Dockerfile          自包含镜像（含 Chromium）
run.py              开发服务器入口
wsgi.py             gunicorn 入口
```

## 本地运行

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 可选：安装审核机器人需要的浏览器
playwright install chromium

python run.py
# http://127.0.0.1:5000
```

默认管理员账号为 `admin / admin123`（首次启动时创建，可用环境变量覆盖）。

### Docker

```bash
docker build -t flavalon .
docker run --rm -p 8080:5000 -v flavalon-data:/data flavalon
# http://127.0.0.1:8080
```

## 配置

全部配置项均可通过环境变量覆盖：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SECRET_KEY` | 开发用固定值 | Flask session 密钥，生产环境务必修改 |
| `DATABASE_PATH` | `data/flavalon.db` | SQLite 文件位置 |
| `PORT` / `HOST` | `5000` / `0.0.0.0` | 监听地址 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` | 初始管理员，仅在建库时生效 |
| `BOT_ENABLED` | `1` | 是否启用审核机器人 |
| `SELF_BASE_URL` | 空 | 机器人访问站点用的地址 |
| `BROWSER_PATH` | 空 | 浏览器可执行文件路径，留空用 Playwright 自带 |
| `BOT_REVIEW_DELAY_MS` | `1500` | 机器人复核时在页面停留的毫秒数 |

## 审核机器人

「每日事项」采用「先审后发」流程：

1. 用户提交日程，状态为 `pending`；
2. 后台线程的机器人登录管理后台，打开复核页；
3. 机器人确认无误后，将日程标记为 `approved` 并对外发布。

机器人默认使用 Playwright 驱动 Chromium 完成复核；当环境中没有可用的浏览器时，
会退化为一次纯 HTTP 访问，保证审核流程不会阻塞。

## 安全说明

- 所有用户提交的内容在展示时都会经过模板自动转义，不会被当作标记解析。
- 管理员口令使用 scrypt 哈希存储。
- 匿名用户仅能访问属于自己的待办、小记与日程。

## 许可证

本项目采用 [GNU GPLv3](./LICENSE) 开源许可证。
