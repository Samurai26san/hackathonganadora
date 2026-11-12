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
ALIAS = 'qwen2.5-7b-instruct-q4_k_m'


def ready() -> bool:
    try:
        with urllib.request.urlopen('http://127.0.0.1:18081/v1/models', timeout=2) as response:
            return any(m['id'] == ALIAS for m in json.load(response)['data'])
    except (OSError, ValueError, KeyError):
        return False


def main() -> None:
    if ready():
        print('Qwen local ya está disponible; se reutiliza.', flush=True)
        return
    folder = ROOT / 'llama.cpp/models'
    folder.mkdir(parents=True, exist_ok=True)
    files = json.loads((ROOT / 'ops/models.json').read_text())['files']
    with (folder / '.download.lock').open('a') as lock:
        while not all((folder / f['name']).is_file() for f in files):
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('Qwen: esperando la descarga activa; se conservan sus checkpoints.', flush=True)
                time.sleep(15)
                continue
            fcntl.flock(lock, fcntl.LOCK_UN)
            subprocess.run([sys.executable, str(ROOT / 'tools/download_models.py'), '--workers', '16'], check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/setup_llama.py')], check=True)
    # Existing files must also match the official hashes before loading them.
    subprocess.run([sys.executable, str(ROOT / 'tools/download_models.py')], check=True)
    binary = ROOT / 'ops/runtime/llama/llama-b12319/llama-server'
    command = [str(binary), '--model', str(folder / files[0]['name']),
               '--alias', ALIAS, '--host', '127.0.0.1', '--port', '18081',
               '--ctx-size', '8192', '--parallel', '1', '--jinja',
               '--device', 'none', '--n-gpu-layers', '0', '--threads', '4',
               '--threads-batch', '4', '--batch-size', '64', '--ubatch-size', '32',
               '--flash-attn', 'on', '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0']
    print('Cargando Qwen2.5-7B real en CPU, puerto 18081.', flush=True)
    os.execv(binary, command)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
