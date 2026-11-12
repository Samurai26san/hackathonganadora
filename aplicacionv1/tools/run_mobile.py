"""Run the existing Flutter MVP on the LAN with a separate local demo API."""
from __future__ import annotations

import argparse
from functools import partial
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
from http.server import ThreadingHTTPServer

from serve_web import Handler, ROOT


def lan_ip() -> str:
    try:
        result = subprocess.run(
            ['ip', '-j', '-4', 'route', 'get', '1.1.1.1'],
            capture_output=True, text=True, timeout=3,
        )
        return json.loads(result.stdout)[0]['prefsrc']
    except (OSError, ValueError, KeyError, IndexError, subprocess.TimeoutExpired):
        return 'IP_DE_TU_PC'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8088)
    args = parser.parse_args()
    if not (ROOT / 'build/web/index.html').is_file():
        raise SystemExit('Falta el build de Flutter. Ejecuta make web-build.')
    python = ROOT / 'backend/.venv/bin/python'
    if not python.is_file():
        raise SystemExit('Falta el entorno backend. Ejecuta make backend-setup.')
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        api_port = reserve.getsockname()[1]

    class MobileHandler(Handler):
        backend_port = api_port

    server = ThreadingHTTPServer(
        ('0.0.0.0', args.port),
        partial(MobileHandler, directory=str(ROOT / 'build/web')),
    )
    server.daemon_threads = True
    address = lan_ip()
    environment = {
        **os.environ,
        'PYTHONPATH': '.', 'APP_ENV': 'development', 'AUTH_MODE': 'demo',
        'COOKIE_SECURE': 'false',
        'BACKEND_CORS_ORIGINS': json.dumps([
            f'http://localhost:{args.port}', f'http://127.0.0.1:{args.port}',
            f'http://{address}:{args.port}',
        ]),
    }
    runtime = ROOT / 'ops/runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / 'mobile-api.log').open('a') as log:
        api = subprocess.Popen([
            str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
            '--port', str(api_port), '--no-access-log',
        ], cwd=ROOT / 'backend', env=environment, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(40):
                if api.poll() is not None:
                    raise RuntimeError('La API no inició. Revisa ops/runtime/mobile-api.log.')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{api_port}/ready', timeout=1):
                        break
                except OSError:
                    time.sleep(0.25)
            else:
                raise RuntimeError('PostgreSQL no está disponible. Inicia docker compose up -d postgres.')
            details = {'url': f'http://{address}:{args.port}', 'web_port': args.port, 'api_port': api_port, 'api_pid': api.pid}
            (runtime / 'mobile.json').write_text(json.dumps(details, indent=2) + '\n')
            print(f'\nMVP: http://{address}:{args.port}', flush=True)
            print(f'En esta PC: http://localhost:{args.port}', flush=True)
            print('Celular y PC deben estar en la misma red WiFi.', flush=True)
            print('Acceso local: tecnico@exb.demo / Demo2026!', flush=True)
            print('Ctrl+C detiene este arranque. Log: ops/runtime/mobile-api.log\n', flush=True)
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            api.terminate()
            try:
                api.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait()


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as error:
        raise SystemExit(f'No se pudo iniciar el MVP: {error}') from None
