#!/bin/sh
set -e

# ============================================================
# 1. 注入动态 flag
#    平台（GZCTF / CTFd / DASCTF）会注入 GZCTF_FLAG / FLAG / DASCTF。
#    flag 写入 web 根之外的 /flag，供审核机器人读取。
#    本地开发未注入时使用占位 flag。
# ============================================================
FLAG_VALUE="${GZCTF_FLAG:-${FLAG:-${DASCTF:-}}}"
if [ -z "$FLAG_VALUE" ]; then
  FLAG_VALUE="flag{local_dev_placeholder}"
fi
printf '%s\n' "$FLAG_VALUE" > /flag
chmod 644 /flag
# 从环境变量中清除，防止通过 env / printenv 直接读到
export GZCTF_FLAG=
export FLAG=
export DASCTF=

# ============================================================
# 2. 数据目录
# ============================================================
mkdir -p /data

# ============================================================
# 3. 启动服务（数据库表在应用启动时自动创建）
# ============================================================
exec "$@"
