# Flavalon —— 自包含 Flask + SQLite 镜像
#
# 单一容器同时提供 Web 服务与后台审核机器人：
#   - gunicorn 提供 Web 服务
#   - 审核机器人使用 Chromium 打开后台复核页

FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 安装 Chromium（审核机器人使用）与基础依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY run.py wsgi.py ./

ENV PORT=5000 \
    HOST=0.0.0.0 \
    DATABASE_PATH=/data/flavalon.db \
    BOT_ENABLED=1 \
    BROWSER_PATH=/usr/bin/chromium \
    SELF_BASE_URL=http://127.0.0.1:5000

VOLUME ["/data"]

EXPOSE 5000
CMD ["gunicorn", "-w", "1", "-k", "gthread", "-b", "0.0.0.0:5000", "wsgi:app"]
