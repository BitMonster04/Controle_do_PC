import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

spec=importlib.util.spec_from_file_location('server',Path(__file__).resolve().parents[1]/'pi/server.py')
server=importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        server.DATA=Path(self.temp.name)
        os.environ['PC_ORIGIN']='https://panel.example'
        self.creds=server.initialize()
        self.cookie=''

    def tearDown(self):
        self.temp.cleanup()

    def request(self,path,data=None,origin='https://panel.example',cookie=None):
        h=server.Handler.__new__(server.Handler)
        h.path='/controle-pc'+path
        h.client_address=('127.0.0.1',1234)
        body=json.dumps(data).encode()
        h.headers={'Content-Length':str(len(body)),'Origin':origin,'Cookie':self.cookie if cookie is None else cookie}
        h.rfile=io.BytesIO(body)
        result={}
        def send(code,payload,cookie=None,content_type=None):
            result.update(code=code,data=payload,cookie=cookie)
        h.send=send
        h.do_GET() if data is None else h.do_POST()
        return result

    def login(self):
        r=self.request('/api/login',{'password':self.creds['panel_password']})
        self.assertEqual(r['code'],200)
        self.cookie=r['cookie'].split(';')[0]
        return r

    def heartbeat(self,blocked=False,ack=None,error=None,token=None):
        return self.request('/api/heartbeat',dict(p_token=self.creds['device_token'] if token is None else token,p_blocked=blocked,p_rule_count=225 if blocked else 0,p_ack=ack,p_error=error),origin='')

    def test_login_cookie_and_authentication(self):
        self.assertEqual(self.request('/api/rpc/pc_status',{})['code'],401)
        r=self.login()
        self.assertIn('HttpOnly',r['cookie']);self.assertIn('Secure',r['cookie']);self.assertIn('SameSite=Strict',r['cookie'])
        self.assertEqual(self.request('/api/session')['data']['session']['user']['id'],'chief')

    def test_csrf_and_rate_limit(self):
        self.assertEqual(self.request('/api/login',{'password':self.creds['panel_password']},origin='https://evil.example')['code'],403)
        for _ in range(6):self.assertEqual(self.request('/api/login',{'password':'wrong'})['code'],401)
        self.assertEqual(self.request('/api/login',{'password':'wrong'})['code'],429)

    def test_agent_requires_token_and_cannot_command(self):
        self.assertEqual(self.heartbeat(token='bad')['code'],403)
        self.assertEqual(self.request('/api/rpc/pc_command',{'p_blocked':True,'p_token':self.creds['device_token']})['code'],401)

    def test_no_automatic_order_on_initial_heartbeat(self):
        self.assertIsNone(self.heartbeat()['data']['action'])
        self.login()
        s=self.request('/api/rpc/pc_status',{})['data']
        self.assertTrue(s['online']);self.assertFalse(s['blocked'])

    def test_confirmed_round_trip_and_audit(self):
        self.login();self.heartbeat()
        r=self.request('/api/rpc/pc_command',{'p_blocked':True})
        self.assertEqual(r['code'],200)
        self.assertEqual(self.heartbeat()['data']['action'],'bloquear')
        s=self.request('/api/rpc/pc_status',{})['data']
        self.assertTrue(s['pending']);self.assertFalse(s['blocked'])
        self.assertEqual(self.request('/api/rpc/pc_command',{'p_blocked':False})['code'],409)
        self.assertIsNone(self.heartbeat(blocked=True,ack=r['data'])['data']['action'])
        s=self.request('/api/rpc/pc_status',{})['data']
        self.assertTrue(s['blocked']);self.assertFalse(s['pending'])
        with server.connect() as db:self.assertEqual(db.execute('select count(*) from audit').fetchone()[0],1)
        rev=self.request('/api/rpc/pc_command',{'p_blocked':False})['data']
        self.assertEqual(self.heartbeat(True)['data']['action'],'desbloquear')
        self.assertIsNone(self.heartbeat(False,rev)['data']['action'])

    def test_error_ack_preserves_actual_state(self):
        self.login();self.heartbeat()
        rev=self.request('/api/rpc/pc_command',{'p_blocked':True})['data']
        self.heartbeat(False,rev,'Firewall recusou')
        s=self.request('/api/rpc/pc_status',{})['data']
        self.assertFalse(s['blocked']);self.assertFalse(s['pending']);self.assertEqual(s['last_error'],'Firewall recusou')

    def test_offline_and_expiration(self):
        self.login()
        self.assertEqual(self.request('/api/rpc/pc_command',{'p_blocked':True})['code'],409)
        self.heartbeat()
        self.request('/api/rpc/pc_command',{'p_blocked':True})
        with server.connect() as db:db.execute('update device set expires=?,last_seen=?',(time.time()-1,time.time()-61))
        s=self.request('/api/rpc/pc_status',{})['data']
        self.assertFalse(s['online']);self.assertFalse(s['pending'])
        self.assertIn('expirou',s['last_error'])
        self.assertIsNone(self.heartbeat()['data']['action'])

    def test_invalid_actions_and_logout(self):
        self.login();self.heartbeat()
        self.assertEqual(self.request('/api/rpc/pc_command',{'p_blocked':'run shell'})['code'],400)
        self.request('/api/logout',{})
        self.assertEqual(self.request('/api/rpc/pc_status',{})['code'],401)

if __name__=='__main__':unittest.main()
