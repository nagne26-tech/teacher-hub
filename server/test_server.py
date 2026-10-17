import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

spec=importlib.util.spec_from_file_location('hub_server', Path(__file__).with_name('server.py'))
hub=importlib.util.module_from_spec(spec)
spec.loader.exec_module(hub)

class AccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        hub.DB=Path(cls.temp.name)/'test.sqlite3'
        hub.init()
        with hub.connect() as db:
            db.execute("INSERT INTO users VALUES('admin','admin@example.com','Owner',?,'admin','approved')",(hub.password_hash('correct-admin-password'),))
        cls.server=hub.ThreadingHTTPServer(('127.0.0.1',0),hub.Handler)
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
        hub.PUBLIC_ORIGIN=cls.base
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
    def request(self,path,data=None,cookie='',origin=None):
        headers={'Cookie':cookie}
        if data is not None:headers.update({'Content-Type':'application/json','Origin':origin or self.base,'X-Hub-Request':'1'})
        req=Request(self.base+'/api/'+path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            with urlopen(req) as r:return r.status,json.load(r),r.headers.get('Set-Cookie','').split(';')[0]
        except HTTPError as e:
            with e:return e.code,json.load(e),''
    def test_approval_and_catalog_access(self):
        self.assertEqual(self.request('register',{'name':'Teacher','email':'teacher@example.com','password':'correct-teacher-password','role':'admin','status':'approved'})[0],200)
        _,login,teacher=self.request('login',{'email':'teacher@example.com','password':'correct-teacher-password'})
        self.assertEqual(login['user']['status'],'pending')
        self.assertEqual(login['user']['role'],'teacher')
        self.assertIn('HttpOnly',self.cookie_security())
        _,_,admin=self.request('login',{'email':'admin@example.com','password':'correct-admin-password'})
        lesson={'name':'Lesson','description':'public','category':'Engineering','url':'https://example.com/class','audience':'class'}
        private={**lesson,'name':'Private','url':'https://example.com/secret','audience':'teacher'}
        self.assertEqual(self.request('apps/save',private,teacher)[0],403)
        self.assertEqual(self.request('teachers',cookie=teacher)[0],403)
        self.assertEqual(self.request('apps/save',lesson,admin)[0],200)
        self.assertEqual(self.request('apps/save',private,admin)[0],200)
        self.assertEqual(len(self.request('apps')[1]['apps']),1)
        self.assertEqual(len(self.request('apps',cookie=teacher)[1]['apps']),1)
        teachers=self.request('teachers',cookie=admin)[1]['users']
        teacher_id=teachers[0]['id']
        self.assertEqual(self.request('teachers/status',{'id':teacher_id,'status':'approved'},teacher)[0],403)
        self.assertEqual(self.request('teachers/status',{'id':teacher_id,'status':'approved'},admin)[0],200)
        self.assertEqual(len(self.request('apps',cookie=teacher)[1]['apps']),2)
        self.request('teachers/status',{'id':teacher_id,'status':'revoked'},admin)
        self.assertEqual(len(self.request('apps',cookie=teacher)[1]['apps']),1)
        self.assertEqual(self.request('apps/save',{**lesson,'url':'javascript:alert(1)'},admin)[0],400)
        self.assertEqual(self.request('apps/save',lesson,admin,origin='https://evil.example')[0],403)
        self.assertEqual(self.request('logout',{},admin)[0],200)
        self.assertEqual(self.request('teachers',cookie=admin)[0],403)
    def cookie_security(self):
        request=Request(self.base+'/api/login',data=json.dumps({'email':'teacher@example.com','password':'correct-teacher-password'}).encode(),headers={'Origin':self.base,'X-Hub-Request':'1'})
        with urlopen(request) as r:return r.headers['Set-Cookie']

if __name__=='__main__':unittest.main()
