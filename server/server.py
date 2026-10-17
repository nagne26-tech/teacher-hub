"""Same-origin hub API and static host. Python 3.10+, standard library only."""
import argparse
import getpass
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get('HUB_DB', ROOT / 'server/data/hub.sqlite3'))
PUBLIC_ORIGIN = os.environ.get('HUB_PUBLIC_ORIGIN', 'http://127.0.0.1:8787').rstrip('/')

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'teacher',status TEXT NOT NULL DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS apps(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,category TEXT NOT NULL,url TEXT NOT NULL,audience TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,count INTEGER NOT NULL,reset INTEGER NOT NULL);
        ''')
    os.chmod(DB, 0o600)

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()

def check_password(password, stored):
    return hmac.compare_digest(password_hash(password, stored.split(':')[0]), stored)

def public_user(user):
    return {k: user[k] for k in ('id', 'email', 'name', 'role', 'status')}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'dist'), **kwargs)

    def log_message(self, fmt, *args):
        pass  # Do not log submitted account data or request paths.

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        super().end_headers()

    def reply(self, code, value, cookie=None):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(raw)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(raw)

    def user(self, db):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            token = cookie['hub_session'].value
        except (KeyError, ValueError):
            return None
        return db.execute('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token=? AND s.expires>?', (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()

    def do_GET(self):
        if self.path.startswith('/api/'):
            return self.api('GET')
        if urlsplit(self.path).path.startswith('/.'):
            return self.send_error(404)
        return super().do_GET()

    def do_POST(self):
        self.api('POST')

    def api(self, method):
        try:
            if method == 'POST':
                if self.headers.get('Origin') != PUBLIC_ORIGIN or self.headers.get('X-Hub-Request') != '1':
                    return self.reply(403, {'error': '같은 사이트에서 다시 시도해주세요.'})
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    return self.reply(413, {'error': '요청 크기를 확인해주세요.'})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError()
            else:
                data = {}
            path = urlsplit(self.path).path
            if path == '/api/diary' or path.startswith('/api/diary/'):
                return self.reply(404, {'error': '요청을 찾을 수 없습니다.'})
            with connect() as db:
                user = self.user(db)
                admin = user and user['role'] == 'admin' and user['status'] == 'approved'
                teacher = user and user['status'] == 'approved'
                if path == '/api/me' and method == 'GET':
                    return self.reply(200, {'user': public_user(user) if user else None})
                if path in ('/api/register', '/api/login') and method == 'POST':
                    now = int(time.time())
                    key = self.client_address[0]
                    record = db.execute('SELECT * FROM attempts WHERE key=?', (key,)).fetchone()
                    if record and record['reset'] > now and record['count'] >= 20:
                        return self.reply(429, {'error': '시도가 많습니다. 15분 후 다시 시도해주세요.'})
                    db.execute('INSERT INTO attempts VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN reset<=? THEN 1 ELSE count+1 END, reset=CASE WHEN reset<=? THEN ? ELSE reset END', (key,now+900,now,now,now+900))
                    db.commit()
                    email = str(data.get('email', '')).strip().lower()
                    password = data.get('password', '')
                    if not isinstance(password, str) or not 12 <= len(password) <= 128 or len(email)>254 or '@' not in email:
                        return self.reply(400, {'error': '이메일과 12~128자 비밀번호를 입력해주세요.'})
                    if path == '/api/register':
                        name = str(data.get('name', '')).strip()
                        if not 1 <= len(name) <= 40:
                            return self.reply(400, {'error': '이름은 1~40자로 입력해주세요.'})
                        try:
                            db.execute('INSERT INTO users(id,email,name,password) VALUES(?,?,?,?)', (secrets.token_hex(16),email,name,password_hash(password)))
                            db.commit()
                        except sqlite3.IntegrityError:
                            pass
                        return self.reply(200, {'message': '가입 요청을 처리했습니다. 로그인 후 승인 상태를 확인해주세요.'})
                    account = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                    stored = account['password'] if account else password_hash('dummy-password-value', '00'*16)
                    if not check_password(password, stored) or account is None:
                        return self.reply(401, {'error': '이메일 또는 비밀번호를 확인해주세요.'})
                    token = secrets.token_urlsafe(32)
                    db.execute('DELETE FROM sessions WHERE expires<=?', (now,))
                    db.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(),account['id'],now+28800))
                    db.commit()
                    secure = '; Secure' if PUBLIC_ORIGIN.startswith('https://') else ''
                    return self.reply(200, {'user': public_user(account)}, 'hub_session='+token+'; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800'+secure)
                if path == '/api/logout' and method == 'POST':
                    cookie = SimpleCookie(self.headers.get('Cookie', ''))
                    if 'hub_session' in cookie:
                        db.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(cookie['hub_session'].value.encode()).hexdigest(),))
                    db.commit()
                    return self.reply(200, {}, 'hub_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0')
                if path == '/api/apps' and method == 'GET':
                    audience = 'teacher' if teacher else 'class'
                    rows = db.execute('SELECT * FROM apps WHERE audience IN (\'class\',?) ORDER BY rowid DESC', (audience,)).fetchall()
                    return self.reply(200, {'apps': [dict(r) for r in rows]})
                if path == '/api/teachers' and method == 'GET':
                    if not admin:
                        return self.reply(403, {'error': '관리자만 확인할 수 있습니다.'})
                    return self.reply(200, {'users': [public_user(r) for r in db.execute("SELECT * FROM users WHERE role='teacher' ORDER BY rowid DESC")]})
                if path == '/api/teachers/status' and method == 'POST':
                    if not admin:
                        return self.reply(403, {'error': '관리자 권한이 필요합니다.'})
                    status = data.get('status')
                    if status not in ('approved', 'revoked'):
                        raise ValueError()
                    result = db.execute("UPDATE users SET status=? WHERE id=? AND role='teacher'", (status,data.get('id')))
                    if result.rowcount != 1:
                        return self.reply(404, {'error': '교사 계정을 찾을 수 없습니다.'})
                    # Check database approval on every subsequent request, including existing sessions.
                    db.commit()
                    return self.reply(200, {})
                if path in ('/api/apps/save', '/api/apps/delete') and method == 'POST':
                    if not admin:
                        return self.reply(403, {'error': '관리자만 앱을 관리할 수 있습니다.'})
                    if path.endswith('delete'):
                        db.execute('DELETE FROM apps WHERE id=?', (data.get('id'),))
                    else:
                        app = {k: str(data.get(k, '')).strip() for k in ('name','description','category','url','audience')}
                        parsed = urlsplit(app['url'])
                        if not 1<=len(app['name'])<=40 or not 1<=len(app['category'])<=20 or len(app['description'])>200 or len(app['url'])>2048 or parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or app['audience'] not in ('class','teacher'):
                            return self.reply(400, {'error': '이름·분류·설명·인터넷 주소와 이용 대상을 확인해주세요.'})
                        app_id = data.get('id') or secrets.token_hex(16)
                        db.execute('INSERT INTO apps VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,category=excluded.category,url=excluded.url,audience=excluded.audience', (app_id,app['name'],app['description'],app['category'],app['url'],app['audience']))
                    db.commit()
                    return self.reply(200, {})
                return self.reply(404, {'error': '요청을 찾을 수 없습니다.'})
        except (ValueError, TypeError, UnicodeError):
            return self.reply(400, {'error': '입력 내용을 확인해주세요.'})
        except Exception:
            return self.reply(500, {'error': '서버 처리 중 오류가 발생했습니다.'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--create-admin', action='store_true')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    init()
    if args.create_admin:
        email = input('관리자 이메일: ').strip().lower()
        name = input('관리자 이름: ').strip()
        password = getpass.getpass('관리자 비밀번호 (12~128자): ')
        if '@' not in email or not 1<=len(name)<=40 or not 12<=len(password)<=128:
            raise SystemExit('이메일·이름·비밀번호 길이를 확인해주세요.')
        with connect() as db:
            db.execute("INSERT INTO users VALUES(?,?,?,?, 'admin','approved')", (secrets.token_hex(16),email,name,password_hash(password)))
        print('관리자 계정을 생성했습니다.')
    else:
        print(f'티처 허브: {PUBLIC_ORIGIN} (Ctrl+C로 종료)')
        ThreadingHTTPServer((args.host,args.port), Handler).serve_forever()
