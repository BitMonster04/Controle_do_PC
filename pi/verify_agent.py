"""Executar no Pi como pccontrol: testa ordem idempotente pela API real."""
import hashlib,json,secrets,sqlite3,time,urllib.request

DB='/var/lib/controle-pc/state.sqlite3'
token=secrets.token_urlsafe(32)
hashed=hashlib.sha256(token.encode()).hexdigest()
with sqlite3.connect(DB) as db:
    db.row_factory=sqlite3.Row
    initial=db.execute('select * from device where id=1').fetchone()
    if initial['last_seen'] is None or time.time()-initial['last_seen']>60:
        raise SystemExit('REMOTA sem contato recente; teste cancelado.')
    original=bool(initial['blocked'])
    db.execute('insert into sessions values(?,?)',(hashed,time.time()+180))
try:
    req=urllib.request.Request('http://127.0.0.1:8795/controle-pc/api/rpc/pc_command',
        data=json.dumps({'p_device':'pc-jogos','p_blocked':original}).encode(),
        headers={'Content-Type':'application/json','Origin':'https://aurora2d.tail8abf1e.ts.net:8443','Cookie':'pc_session='+token})
    revision=json.load(urllib.request.urlopen(req,timeout=10))
    deadline=time.monotonic()+75
    while time.monotonic()<deadline:
        with sqlite3.connect(DB) as db:
            db.row_factory=sqlite3.Row
            current=db.execute('select * from device where id=1').fetchone()
        if current['ack']>=revision:
            if current['error']:raise SystemExit('Agente informou falha: '+current['error'])
            if bool(current['blocked'])!=original:raise SystemExit('Estado diferente do solicitado.')
            print(json.dumps({'result':'confirmed','revision':revision,'blocked':bool(current['blocked']),'rule_count':current['rule_count']}))
            break
        time.sleep(3)
    else:raise SystemExit('A ordem nao foi confirmada dentro do prazo do teste.')
finally:
    with sqlite3.connect(DB) as db:db.execute('delete from sessions where token_hash=?',(hashed,))
