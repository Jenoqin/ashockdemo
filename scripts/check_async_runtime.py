#!/usr/bin/env python3
"""Fail fast when the selected event loop cannot run sync FastAPI routes."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import threading
from pathlib import Path


PROBE_TIMEOUT_SECONDS = 5


def _probe_thread_socket_wakeup() -> None:
    """Verify the primitive used by asyncio.call_soon_threadsafe()."""
    reader, writer = socket.socketpair()
    errors: list[BaseException] = []

    def send_wakeup() -> None:
        try:
            writer.send(b"\0")
        except BaseException as exc:  # surfaced in the parent thread below
            errors.append(exc)

    try:
        worker = threading.Thread(target=send_wakeup, name="runtime-wakeup-probe")
        worker.start()
        worker.join(timeout=1)
        if worker.is_alive():
            raise RuntimeError("工作线程未能在 1 秒内完成事件循环唤醒写入")
        if errors:
            raise RuntimeError(
                "执行环境禁止工作线程写入事件循环唤醒 socket："
                f"{errors[0]!r}"
            ) from errors[0]

        reader.settimeout(1)
        if reader.recv(1) != b"\0":
            raise RuntimeError("事件循环唤醒 socket 未收到预期数据")
    finally:
        reader.close()
        writer.close()


def _run_fastapi_probe(loop_name: str) -> None:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child",
        loop_name,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{loop_name} 路径在 {PROBE_TIMEOUT_SECONDS} 秒内未完成同步路由请求"
        ) from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"{loop_name} 路径的同步路由探测失败"
            + (f"：{detail}" if detail else "")
        )


def _child_probe(loop_name: str) -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/probe")
    def probe() -> dict[str, bool]:
        return {"ok": True}

    backend_options = {"use_uvloop": True} if loop_name == "uvloop" else {}
    with TestClient(
        app,
        backend="asyncio",
        backend_options=backend_options,
    ) as client:
        response = client.get("/probe")

    if response.status_code != 200 or response.json() != {"ok": True}:
        raise RuntimeError(
            f"unexpected probe response: {response.status_code} {response.text}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", choices=("all", "asyncio", "uvloop"), default="all")
    parser.add_argument("--child", choices=("asyncio", "uvloop"), help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.child:
        return _child_probe(args.child)

    loops = ("asyncio", "uvloop") if args.loop == "all" else (args.loop,)
    for loop_name in loops:
        try:
            if loop_name == "asyncio":
                _probe_thread_socket_wakeup()
            _run_fastapi_probe(loop_name)
        except RuntimeError as exc:
            print(f"[FAIL] {exc}", file=sys.stderr)
            if loop_name == "asyncio":
                print(
                    "当前环境不满足默认 asyncio 的跨线程唤醒能力；"
                    "请改用允许该 socket 操作的宿主环境。不要通过降级 AnyIO 或异步化阻塞路由规避。",
                    file=sys.stderr,
                )
            return 1
        print(f"[PASS] {loop_name} 同步 FastAPI 路由")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
