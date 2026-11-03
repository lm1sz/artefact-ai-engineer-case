"""Local-only web UI for the real agent; credentials stay in Python."""
import argparse
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
from time import monotonic
from urllib.parse import urlsplit

from chatbot.agent import Agent, ProviderError
from chatbot.data import ROOT, Store, localizar_dados
from chatbot.providers import carregar_ambiente, criar_provedor, configuracao_provedor
from chatbot.tools import Session, Tools


class EstadoWeb:
    def __init__(self, store, provider, settings, customer_id=None):
        self.store, self.provider, self.settings = store, provider, settings
        self.customer_id = customer_id
        self.sessions = {}
        self.lock = threading.Lock()
        self.model_lock = threading.Lock()

    def sessao(self, token):
        with self.lock:
            now = monotonic()
            self.sessions = {k: v for k, v in self.sessions.items() if now - v['used'] < 3600}
            if token not in self.sessions:
                if len(self.sessions) >= 32:
                    return None, None, False
                token = secrets.token_urlsafe(32)
                self.sessions[token] = {'csrf': secrets.token_urlsafe(32), 'used': now,
                    'agent': Agent(Tools(self.store, Session(self.customer_id)), self.provider)}
                fresh = True
            else:
                fresh = False
            session = self.sessions[token]
            session['used'] = now
            return token, session, fresh


def criar_handler(state, ui_directory=None):
    ui_directory = ui_directory or Path(__file__).resolve().parent

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _headers(self, status, mime, data, cookie=None):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
            if cookie:
                self.send_header('Set-Cookie', f'emporio_session={cookie}; Path=/; HttpOnly; SameSite=Strict')
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status, value, cookie=None):
            self._headers(status, 'application/json; charset=utf-8', json.dumps(value, ensure_ascii=False).encode(), cookie)

        def _local(self):
            host = self.headers.get('Host', '')
            port = self.server.server_address[1]
            allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
            origin = self.headers.get('Origin')
            if host not in allowed or (origin is not None and origin != f'http://{host}'):
                self._json(403, {'error': 'Origem não permitida.'})
                return False
            return True

        def _session(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie', ''))
                token = cookie['emporio_session'].value if 'emporio_session' in cookie else None
            except CookieError:
                token = None
            return state.sessao(token)

        def do_GET(self):
            if not self._local():
                return
            path = urlsplit(self.path).path
            if path == '/api/session':
                token, session, fresh = self._session()
                if session is None:
                    return self._json(429, {'error': 'Limite de sessões locais. Tente mais tarde.'})
                return self._json(200, {'csrf': session['csrf'], 'provider': state.settings['provider'],
                    'model': state.settings['model'], 'demo_customer_id': state.customer_id}, token if fresh else None)
            files = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/index.html': ('index.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if path not in files:
                return self._json(404, {'error': 'Não encontrado.'})
            name, mime = files[path]
            try:
                data = (ui_directory / name).read_bytes()
            except OSError:
                return self._json(404, {'error': 'Interface indisponível.'})
            self._headers(200, mime, data)

        def do_POST(self):
            if not self._local():
                return
            path = urlsplit(self.path).path
            if path not in ('/api/chat', '/api/reset'):
                return self._json(404, {'error': 'Não encontrado.'})
            _, session, fresh = self._session()
            if session is None:
                return self._json(429, {'error': 'Limite de sessões locais.'})
            csrf = self.headers.get('X-CSRF-Token', '')
            if fresh or not csrf.isascii() or not secrets.compare_digest(csrf, session['csrf']):
                return self._json(403, {'error': 'Sessão inválida. Recarregue a página.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20000:
                    raise ValueError()
                payload = json.loads(self.rfile.read(length))
                expected = {'message'} if path == '/api/chat' else set()
                if not isinstance(payload, dict) or set(payload) != expected:
                    raise ValueError()
                if path == '/api/chat' and (not isinstance(payload['message'], str)
                        or not payload['message'].strip() or len(payload['message']) > 4000):
                    raise ValueError()
            except (ValueError, UnicodeError):
                return self._json(400, {'error': 'Mensagem inválida; use de 1 a 4.000 caracteres.'})
            if not state.model_lock.acquire(blocking=False):
                return self._json(429, {'error': 'Há uma resposta em andamento. Aguarde antes de enviar outra mensagem.'})
            try:
                if path == '/api/reset':
                    session['agent'].limpar_historico()
                    return self._json(200, {'ok': True})
                reply = session['agent'].perguntar(payload['message'])
                self._json(200, {'answer': reply.text, 'tools': reply.tools, 'checks': reply.checks})
            except ProviderError as error:
                self._json(429 if hasattr(error, 'retry_after') else 502, {
                    'error': str(error), 'retry_after': getattr(error, 'retry_after', None),
                    'reason': getattr(error, 'reason', None)})
            except Exception:
                self._json(500, {'error': 'Não foi possível concluir a resposta. Tente novamente.'})
            finally:
                state.model_lock.release()

    return Handler


def principal():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--demo-customer-id', type=int, help='Trusted local demo identity, never a browser input.')
    args = parser.parse_args()
    carregar_ambiente(ROOT / '.env')
    store = Store(localizar_dados(os.getenv('EMPORIO_DATA_DIR') or None))
    if args.demo_customer_id is not None and args.demo_customer_id not in store.customers:
        parser.error('Unknown demo customer id.')
    state = EstadoWeb(store, criar_provedor(), configuracao_provedor(), args.demo_customer_id)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), criar_handler(state))
    server.daemon_threads = True
    print(f'Empório UI: http://127.0.0.1:{server.server_address[1]} — {state.settings["provider"]} / {state.settings["model"]}', flush=True)
    print(f'Local demonstration only. Customer session: {args.demo_customer_id or "guest"}. Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    principal()
