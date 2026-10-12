# Flavalon —— 审核机器人 XSS

> 难度：Rookie（入门）
> 考点：`存储型 XSS`、`先审后发的审核机器人`、`前端转义 != 服务端渲染`
> 目标：读取 web 根之外的 `/flag`（由平台注入，仅管理员后台可读）

## 一、题目背景（给选手）

Flavalon 是一个自托管的个人日程应用。用户可以把想公开的「每日事项」提交上来，
**先审后发**：所有投稿都会进入审核队列，由一个后台机器人代为复核，通过后再对外发布。

> 站点地址：`http://<host>:8080/`
> 默认管理员账号：`admin / admin123`（题目中的机器人会自动使用它登录复核）

机器人复核时会打开管理后台的审核页，因此在审核页执行的一切脚本都以**管理员身份**运行。

## 二、部署说明（给运维/平台）

与 `Rookie2026/ahnu-share-map`、`KickOff2026` 采用相同约定：

- 单容器镜像（Flask + SQLite + Chromium），Web 服务与审核机器人同进程；
- `docker-entrypoint.sh` 将 `${GZCTF_FLAG}` 写入 **web 根之外** 的 `/flag`，
  随后从环境变量中清除，防止 `env` / `printenv` 读取；
- 本地测试用 `docker-compose.yml` 中的占位 flag。

### 本地运行

```bash
docker compose up --build -d
# http://127.0.0.1:8080
python3 solve.py http://127.0.0.1:8080
```

### 文件清单

```
app/                     Flask 应用
  bot.py                 后台审核机器人（Playwright / Chromium）
  routes/api.py          普通用户 API（含漏洞点：/api/webhook 回连接收）
  store.py               数据访问层
  schema.sql             数据库结构（含 webhook_hits）
  templates/admin/review.html   审核页（漏洞 sink）
Dockerfile               自包含镜像
docker-entrypoint.sh     flag 注入 + 启动
docker-compose.yml       本地起题
solve.py                 官方 exp（纯标准库）
```

## 三、漏洞链

1. **提交带脚本的日程。** 普通用户在「每日事项」提交正文，例如：

   ```html
   <img src=x onerror="fetch('/admin/flag').then(r=>r.text()).then(t=>fetch('/api/webhook/me',{method:'POST',body:t}))">
   ```

2. **内容进入 pending 队列。** 后端原样入库（`agenda.content`），不做 HTML 清洗。

3. **审核机器人触发 sink。** `bot.py` 轮询 pending，登录管理员后台并打开
   `/admin/queue/<id>`。该页面用 `{{ item.content | safe }}` 渲染正文，
   浏览器把投稿内容当作 HTML 解析，脚本以管理员会话执行。

4. **外带 flag。** 脚本调用 `/admin/flag`（仅管理员可读），把结果 POST 到
   `/api/webhook/<token>`，攻击者再 GET 该接口即可拿到 flag。

## 四、修复建议

- 审核页关闭 `| safe`，让模板自动转义投稿内容；
- 若确需渲染 Markdown/富文本，应在服务端用白名单过滤（如 `bleach` / `nh3`）；
- 审核机器人使用独立、最小权限的账号，且不要在同一会话中暴露 `/admin/flag`；
- 对 `httpOnly`、`SameSite` 与 CSRF 做纵深防御。
