#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

VITE="$FRONTEND_DIR/node_modules/.bin/vite"

if ! UV_BIN="$(command -v uv)"; then
  echo "错误：找不到 uv。" >&2
  echo "请先按照 README.md 的“环境要求”章节安装 uv。" >&2
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/uv.lock" ]]; then
  echo "错误：找不到后端锁文件 $BACKEND_DIR/uv.lock" >&2
  exit 1
fi

if [[ ! -x "$VITE" ]]; then
  echo "错误：前端依赖尚未安装（找不到 $VITE）" >&2
  echo "请先运行：npm --prefix frontend ci" >&2
  exit 1
fi

backend_pid=""
frontend_pid=""

cleanup() {
  trap - EXIT INT TERM
  echo
  echo "正在停止前后端服务..."

  [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true
  [[ -z "$frontend_pid" ]] || kill "$frontend_pid" 2>/dev/null || true

  [[ -z "$backend_pid" ]] || wait "$backend_pid" 2>/dev/null || true
  [[ -z "$frontend_pid" ]] || wait "$frontend_pid" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "正在启动 QuantLab..."

(
  cd "$BACKEND_DIR"
  "$UV_BIN" run --locked --extra dev \
    python ../scripts/check_async_runtime.py --loop uvloop
)

(
  cd "$BACKEND_DIR"
  exec "$UV_BIN" run --locked --extra dev \
    uvicorn quantlab.main:app --reload --port 8000 --loop uvloop
) &
backend_pid=$!

(
  cd "$FRONTEND_DIR"
  exec "$VITE" --host 127.0.0.1 --port 5173 --strictPort
) &
frontend_pid=$!

echo "前端：http://127.0.0.1:5173"
echo "API 文档：http://127.0.0.1:8000/docs"
echo "按 Ctrl+C 停止全部服务。"
echo

set +e
wait -n "$backend_pid" "$frontend_pid"
exit_code=$?
set -e

if [[ $exit_code -ne 0 ]]; then
  echo "有一个服务异常退出（状态码：$exit_code）。" >&2
fi

exit "$exit_code"
