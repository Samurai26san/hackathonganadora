"""Optional local-only static server. Python 3 standard library only."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import threading
import webbrowser

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 8080), partial(SimpleHTTPRequestHandler, directory=str(root)))
    except OSError as exc:
        print('No se pudo abrir el puerto 8080:', exc)
        print('Puedes abrir index.html directamente con Chrome o Edge.')
        input('Pulsa Enter para cerrar...')
        raise SystemExit(1)
    print('ExB Finanzas local: http://127.0.0.1:8080')
    print('No se conecta a servicios externos. Cierra con Ctrl+C.')
    threading.Timer(0.5, lambda: webbrowser.open('http://127.0.0.1:8080')).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')
    finally:
        server.server_close()
