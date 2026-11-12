"""Start the real pinned Qwen model locally; resume downloads when necessary."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ALIAS = "qwen2.5-7b-instruct-q4_k_m"


def progress() -> str:
    folder = ROOT / "llama.cpp/models"
    files = json.loads((ROOT / "ops/models.json").read_text())["files"]
    total = sum(item["size"] for item in files)
    complete = 0
    for item in files:
        target = folder / item["name"]
        if target.is_file() and target.stat().st_size == item["size"]:
            complete += item["size"]
            continue
        checkpoint = target.with_name(target.name + ".ranges.json")
        try:
            state = json.loads(checkpoint.read_text())
            complete += sum(
                max(0, min(state["block"], item["size"] - i * state["block"]))
                for i in set(state["completed"])
            )
        except (OSError, ValueError, KeyError):
            pass
    return f"Qwen: descarga {complete / total:.1%} ({complete / 1e9:.2f}/{total / 1e9:.2f} GB). Después se verificará y cargará el modelo."


def ready() -> bool:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:18081/v1/models", timeout=2
        ) as response:
            return any(m["id"] == ALIAS for m in json.load(response)["data"])
    except (OSError, ValueError, KeyError):
        return False


def main() -> None:
    if ready():
        print("Qwen local ya está disponible; se reutiliza.", flush=True)
        return
    folder = ROOT / "llama.cpp/models"
    folder.mkdir(parents=True, exist_ok=True)
    files = json.loads((ROOT / "ops/models.json").read_text())["files"]
    with (folder / ".download.lock").open("a") as lock:
        while not all((folder / f["name"]).is_file() for f in files):
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(progress(), flush=True)
                time.sleep(30)
                continue
            fcntl.flock(lock, fcntl.LOCK_UN)
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/download_models.py"),
                    "--workers",
                    "16",
                ],
                check=True,
            )
    subprocess.run([sys.executable, str(ROOT / "tools/setup_llama.py")], check=True)
    # Existing files must also match the official hashes before loading them.
    subprocess.run([sys.executable, str(ROOT / "tools/download_models.py")], check=True)
    binary = ROOT / "ops/runtime/llama/llama-b12319/llama-server"
    command = [
        str(binary),
        "--model",
        str(folder / files[0]["name"]),
        "--alias",
        ALIAS,
        "--host",
        "127.0.0.1",
        "--port",
        "18081",
        "--ctx-size",
        "8192",
        "--parallel",
        "1",
        "--jinja",
        "--no-repack",
        "--no-warmup",
        "--device",
        "none",
        "--n-gpu-layers",
        "0",
        "--threads",
        "4",
        "--threads-batch",
        "4",
        "--batch-size",
        "256",
        "--ubatch-size",
        "128",
        "--flash-attn",
        "on",
        "--cache-type-k",
        "q8_0",
        "--cache-type-v",
        "q8_0",
    ]
    print("Cargando Qwen2.5-7B real en CPU, puerto 18081.", flush=True)
    os.execv(binary, command)


if __name__ == "__main__":
    try:
        if "--status" in sys.argv:
            print("Qwen local está disponible." if ready() else progress())
        else:
            main()
    except KeyboardInterrupt:
        pass
