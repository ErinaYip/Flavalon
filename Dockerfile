# Flavalon —— 自包含 Flask + SQLite 镜像
#
# 站点与后台审核机器人打包在同一容器内：
#   - gunicorn 提供 Web 服务
#   - 机器人用 Playwright/Chromium 打开后台审核页

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
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PORT=5000 \
    HOST=0.0.0.0 \
    DATABASE_PATH=/data/flavalon.db \
    FLAG_PATH=/flag \
    BOT_ENABLED=1 \
    BROWSER_PATH=/usr/bin/chromium \
    SELF_BASE_URL=http://127.0.0.1:5000

VOLUME ["/data"]

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["gunicorn", "-w", "1", "-k", "gthread", "-b", "0.0.0.0:5000", "wsgi:app"]
