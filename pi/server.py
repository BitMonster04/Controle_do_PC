"""Painel privado com agente restrito a dois estados; Python padrao, SQLite."""
import argparse
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get('PC_DATA', '/var/lib/controle-pc'))
PREFIX = '/controle-pc'

@contextmanager
def connect():
    db = sqlite3.connect(DATA / 'state.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    DATA.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript('''
          create table if not exists device (
            id integer primary key check(id=1), token_hash text not null,
            last_seen real, blocked integer, rule_count integer,
            revision integer not null default 0, ack integer not null default 0,
            desired integer, expires real, error text);
          create table if not exists sessions (token_hash text primary key, expires real not null);
          create table if not exists settings (id integer primary key check(id=1), salt text not null, password_hash text not null);
          create table if not exists audit (id integer primary key, at real not null, blocked integer not null, revision integer not null);
          create table if not exists attempts (address text primary key, count integer not null, until real not null);
          create table if not exists phone_links (token_hash text primary key, expires real not null, used integer not null default 0);
          create table if not exists phone_sessions (token_hash text primary key);
        ''')
        # Preserva o celular de teste ja autorizado antes dos acessos separados.
        for table in ('phone_links','phone_sessions'):
            columns={row['name'] for row in db.execute(f'pragma table_info({table})')}
            if 'label' not in columns:
                db.execute(f"alter table {table} add column label text not null default 'teste'")
        if db.execute('select 1 from settings').fetchone():
            return None
        password = secrets.token_urlsafe(18)
        agent = secrets.token_hex(32)
        salt = secrets.token_hex(16)
        db.execute('insert into settings values(1,?,?)', (salt, password_hash(password, salt)))
        db.execute('insert into device(id,token_hash) values(1,?)', (digest(agent),))
        return {'panel_password': password, 'device_token': agent}

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()

def state(db):
    d = db.execute('select * from device where id=1').fetchone()
    return dict(name='PC Giovanni', online=bool(d['last_seen'] and d['last_seen'] > time.time()-60),
                blocked=None if d['blocked'] is None else bool(d['blocked']), rule_count=d['rule_count'],
                last_seen=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(d['last_seen'])) if d['last_seen'] else None,
                pending=bool(d['revision']>d['ack'] and d['expires']>time.time()),
                last_error='A ordem expirou. Tente novamente.' if d['revision']>d['ack'] and d['expires']<=time.time() else d['error'])

class Handler(BaseHTTPRequestHandler):
    server_version = 'ControlePC'

    def log_message(self, *_):
        pass  # Nao registra cookies, corpo nem credenciais.

    def send(self, code, payload, cookie=None, content_type='application/json; charset=utf-8'):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(raw)

    def session(self, db):
        try:
            c = SimpleCookie(self.headers.get('Cookie', ''))
            token = c['pc_session'].value
        except (KeyError, ValueError):
            return False
        return bool(db.execute('select 1 from sessions where token_hash=? and expires>?', (digest(token),time.time())).fetchone())

    def do_GET(self):
        p = route(self.path)
        if p == '/api/session':
            with connect() as db:
                self.send(200, {'session': {'user': {'id':'chief'}} if self.session(db) else None})
            return
        files = {'/':('index.html','text/html; charset=utf-8'), '':('index.html','text/html; charset=utf-8'),
                 '/style.css':('style.css','text/css; charset=utf-8'), '/app.js':('app.js','text/javascript; charset=utf-8'),
                 '/api.js':('pi/api.js','text/javascript; charset=utf-8'), '/config.js':('pi/config.js','text/javascript; charset=utf-8')}
        files.update({'/manifest.webmanifest':('manifest.webmanifest','application/manifest+json'),
                      '/pwa.js':('pwa.js','text/javascript; charset=utf-8'),'/sw.js':('sw.js','text/javascript; charset=utf-8'),
                      '/icon-192.png':('icon-192.png','image/png'),'/icon-512.png':('icon-512.png','image/png')})
        if p not in files:
            self.send(404, {'message':'Nao encontrado.'}); return
        name, mime = files[p]
        self.send(200, (BASE/name).read_bytes(), content_type=mime)

    def do_POST(self):
        p = route(self.path)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>8192:
                self.send(413, {'message':'Tamanho invalido.'}); return
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError()
        except (ValueError, UnicodeError):
            self.send(400, {'message':'JSON invalido.'}); return
        # Agente usa segredo e HTTPS; navegador exige origem exata e cookie.
        if p != '/api/heartbeat':
            origin=self.headers.get('Origin','')
            expected=os.environ.get('PC_ORIGIN','')
            if not expected or origin != expected:
                self.send(403, {'message':'Origem nao autorizada.'}); return
        with connect() as db:
            if p == '/api/enroll':
                code=data.get('code','')
                if not isinstance(code,str) or len(code)>200:
                    self.send(403,{'message':'Link de ativacao invalido.'}); return
                db.execute('begin immediate')
                link=db.execute('select * from phone_links where token_hash=?',(digest(code),)).fetchone()
                if not link or link['used'] or link['expires']<time.time():
                    self.send(403,{'message':'Este link expirou ou ja foi usado. Solicite um novo link de ativacao.'}); return
                token=secrets.token_urlsafe(32)
                lifetime=30*86400
                db.execute('delete from sessions where token_hash in (select token_hash from phone_sessions where label=?)',(link['label'],))
                db.execute('delete from phone_sessions where label=?',(link['label'],))
                db.execute('update phone_links set used=1 where token_hash=?',(digest(code),))
                db.execute('insert into sessions values(?,?)',(digest(token),time.time()+lifetime))
                db.execute('insert into phone_sessions(token_hash,label) values(?,?)',(digest(token),link['label']))
                self.send(200,{'session':{'user':{'id':'chief'}}},cookie=f'pc_session={token}; Path=/controle-pc/; HttpOnly; Secure; SameSite=Strict; Max-Age={lifetime}')
                return
            if p == '/api/login':
                address=self.headers.get('X-Real-IP',self.client_address[0])
                a=db.execute('select * from attempts where address=?',(address,)).fetchone()
                if a and a['until']>time.time() and a['count']>=6:
                    self.send(429, {'message':'Aguarde 10 minutos antes de tentar novamente.'}); return
                row=db.execute('select * from settings').fetchone()
                supplied=data.get('password','')
                if not isinstance(supplied,str) or not hmac.compare_digest(password_hash(supplied,row['salt']),row['password_hash']):
                    count=a['count']+1 if a and a['until']>time.time() else 1
                    db.execute('insert or replace into attempts values(?,?,?)',(address,count,time.time()+600))
                    self.send(401, {'message':'Senha do painel incorreta.'}); return
                db.execute('delete from attempts where address=?',(address,))
                token=secrets.token_urlsafe(32)
                db.execute('delete from sessions where expires<?',(time.time(),))
                db.execute('insert into sessions values(?,?)',(digest(token),time.time()+43200))
                self.send(200, {'session':{'user':{'id':'chief'}}}, cookie=f'pc_session={token}; Path=/controle-pc/; HttpOnly; Secure; SameSite=Strict; Max-Age=43200')
                return
            if p == '/api/heartbeat':
                d=db.execute('select * from device where id=1').fetchone()
                token=data.get('p_token','')
                if not isinstance(token,str) or not hmac.compare_digest(digest(token),d['token_hash']):
                    self.send(403, {'message':'Agente nao autorizado.'}); return
                blocked=data.get('p_blocked'); count=data.get('p_rule_count')
                if type(blocked) is not bool or type(count) is not int or count<0:
                    self.send(400, {'message':'Estado invalido.'}); return
                error=data.get('p_error')
                if error is not None and not isinstance(error,str):
                    self.send(400,{'message':'Erro invalido.'}); return
                ack=d['ack']
                if data.get('p_ack')==d['revision'] and (error or blocked==bool(d['desired'])):
                    ack=d['revision']
                db.execute('update device set last_seen=?,blocked=?,rule_count=?,ack=?,error=? where id=1',
                           (time.time(),int(blocked),count,ack,error[:500] if error else None))
                action=('bloquear' if d['desired'] else 'desbloquear') if d['revision']>ack and d['expires']>time.time() else None
                self.send(200, {'revision':d['revision'],'action':action}); return
            if not self.session(db):
                self.send(401, {'message':'Entre no painel para continuar.'}); return
            if p == '/api/logout':
                c=SimpleCookie(self.headers.get('Cookie',''))
                db.execute('delete from sessions where token_hash=?',(digest(c['pc_session'].value),))
                self.send(200, {}, cookie='pc_session=; Path=/controle-pc/; HttpOnly; Secure; SameSite=Strict; Max-Age=0'); return
            if p == '/api/rpc/pc_status':
                self.send(200,state(db)); return
            if p == '/api/rpc/pc_command':
                db.execute('begin immediate')
                s=state(db)
                if not s['online'] or s['pending']:
                    self.send(409,{'message':'Maquina offline ou ordem em andamento.'}); return
                desired=data.get('p_blocked')
                if type(desired) is not bool:
                    self.send(400,{'message':'Acao invalida.'}); return
                db.execute('update device set desired=?,revision=revision+1,expires=?,error=null where id=1',(int(desired),time.time()+120))
                rev=db.execute('select revision from device where id=1').fetchone()[0]
                db.execute('insert into audit(at,blocked,revision) values(?,?,?)',(time.time(),int(desired),rev))
                self.send(200, rev); return
            self.send(404,{'message':'Nao encontrado.'})

def route(path):
    p=urlsplit(path).path
    return p[len(PREFIX):] if p==PREFIX or p.startswith(PREFIX+'/') else p

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--init',action='store_true')
    ap.add_argument('--port',type=int,default=8795)
    ap.add_argument('--phone-link',action='store_true')
    ap.add_argument('--phone-name',choices=['teste','chefia'],default='teste')
    ap.add_argument('--revoke-phone',choices=['teste','chefia'])
    args=ap.parse_args()
    if args.revoke_phone:
        initialize()
        with connect() as db:
            db.execute('delete from sessions where token_hash in (select token_hash from phone_sessions where label=?)',(args.revoke_phone,))
            db.execute('delete from phone_sessions where label=?',(args.revoke_phone,))
            db.execute('delete from phone_links where label=?',(args.revoke_phone,))
        print('Acesso revogado somente para: '+args.revoke_phone)
    elif args.phone_link:
        initialize()
        code=secrets.token_urlsafe(32)
        with connect() as db:
            db.execute('delete from phone_links where label=?',(args.phone_name,))
            db.execute('insert into phone_links(token_hash,expires,label) values(?,?,?)',(digest(code),time.time()+86400,args.phone_name))
        print('https://aurora2d.tail8abf1e.ts.net:8443/controle-pc/#ativar='+code)
    elif args.init:
        result=initialize()
        print(json.dumps(result) if result else 'Ja inicializado; credenciais preservadas.')
    else:
        if not (DATA/'state.sqlite3').exists(): raise SystemExit('Execute --init primeiro.')
        ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
