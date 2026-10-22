"""Additional host-only regressions; deliberately separate from D1's 14 cases."""
import json, os, socket, subprocess, sys, time, unittest, http.client
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ps_service import Service, Client, ROOT, OUT, EXE

class Boundary(Service):
    def test_connection_exhaustion_stop(self):
        self.reference();state=self.c.call('/state')
        cookie='; '.join(c.name+'='+c.value for c in self.c.jar)
        streams=[]
        for _ in range(4):
            stream=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
            stream.request('GET','/api/v1/events',headers={'Cookie':cookie})
            response=stream.getresponse();self.assertEqual(response.status,200)
            streams.append((stream,response))
        self.addCleanup(lambda:[(r.close(),c.close()) for c,r in streams])
        pool=ThreadPoolExecutor(max_workers=1);self.addCleanup(pool.shutdown)
        request={'parameter_version':state['parameter_version'],'start_position_id':state['position']['position_id'],'task':{'points':[{'xyz_mm':[5 if i%2==0 else 0,0,-140]} for i in range(1000)]}}
        future=pool.submit(self.c.call,'/preview','POST',request,error='PREVIEW_STALE')
        time.sleep(.03)
        peers=[]
        self.addCleanup(lambda:[p.close() for p in peers])
        # Fill all ordinary workers with complete headers and incomplete bodies.
        for _ in range(32):
            p=socket.create_connection(('127.0.0.1',self.port),timeout=1)
            p.sendall((f'POST /api/v1/preview HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nContent-Length: 10000\r\nContent-Type: application/json\r\n\r\n').encode())
            peers.append(p)
        time.sleep(.15)
        # Also exhaust pending header admission, exercising its bounded eviction.
        for _ in range(64):
            p=socket.create_connection(('127.0.0.1',self.port),timeout=1)
            p.sendall(b'GET /');peers.append(p)
        start=time.perf_counter();self.c.call('/stop','POST',{});self.idle()
        elapsed=time.perf_counter()-start
        self.assertLess(elapsed,.5)
        future.result(timeout=10)
        self.metrics.append({'case':'4_SSE_long_plan_ordinary_exhaustion_64_partial_headers_STOP','seconds':elapsed})

    def test_cross_boot_log_content_and_identity(self):
        old=self.c.call('/state')['boot_id']
        before=int(self.c.call('/state')['logs']['dropped'])
        burst=self.c.call('/simulation/inject','POST',{'kind':'log_burst','count':'20'})
        accepted=20-(int(burst['dropped'])-before)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            stats=self.c.call('/state')['logs']
            if stats['queue_depth']==0 and stats['last_flushed_event_id']==stats['last_event_id']:break
            time.sleep(.01)
        first=self.c.call('/logs/snapshots','POST',{'component':'simulation'})
        expected=self.c.call('/logs?snapshot='+first['snapshot_id'])['events']
        self.assertEqual(len(expected),accepted);self.assertGreater(accepted,0)
        self.proc.terminate();self.proc.communicate(timeout=5)
        # Preserve evidence of interrupted, corrupt and oversized archived records.
        log=self.directory/'data/logs/events.jsonl'
        with log.open('ab') as f:f.write(b'{bad}\n'+b'x'*9000+b'\n{"partial":')
        self.launch();self.c=Client(self.base,self.token)
        boots=self.c.call('/logs/boots');self.assertIn(old,boots['boot_ids'])
        self.assertGreater(int(boots['archive_errors']),0)
        snap=self.c.call('/logs/snapshots','POST',{'boot_id':old,'component':'simulation'})
        self.assertEqual(snap['boot_id'],old);self.assertTrue(snap['gaps'])
        actual=self.c.call('/logs?snapshot='+snap['snapshot_id'])['events'];self.assertEqual(actual,expected)
        url=self.base+'/api/v1/logs/export?snapshot='+snap['snapshot_id']
        export=self.c.open.open(url).read();lines=[json.loads(x) for x in export.splitlines()]
        self.assertEqual(lines[1:],expected);self.assertEqual(lines[0]['count'],accepted)
        r=actual[0];self.assertEqual(self.c.call('/logs/'+r['event_id']+'?boot_id='+old),r)
        current=self.c.call('/logs/snapshots','POST',{'component':'simulation'})
        self.assertEqual(current['count'],0)
        self.c.call('/logs/snapshots','POST',{'boot_id':'../events.jsonl'},error='FORMAT')
        self.c.call('/logs/snapshots','POST',{'boot_id':'unknown_boot'},error='LOG_RETIRED')
        self.c.call('/simulation/inject','POST',{'kind':'log_burst','count':'3'})
        self.assertEqual(self.c.open.open(url).read(),export)

    def test_browser_generation_and_http_capabilities(self):
        result=subprocess.run(['node','tests/ps_jog_edges.cjs'],cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_browser_release_live_service(self):
        self.reference();self.c.call('/mode','POST',{'mode':'manual'})
        config={'base':self.base,'cookie':'; '.join(c.name+'='+c.value for c in self.c.jar),'csrf':self.c.csrf}
        env=os.environ.copy();env['PS_BROWSER_TEST']=json.dumps(config)
        result=subprocess.run(['node','tests/ps_boundary.cjs'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.idle()
        self.assertIsNone(self.c.call('/state')['command'])

    def test_backend_fail_closed_and_injection_disabled(self):
        for mode in ('hardware','invalid'):
            p=subprocess.run([str(EXE),'--backend',mode],cwd=ROOT,capture_output=True,text=True,timeout=5)
            self.assertNotEqual(p.returncode,0);self.assertIn('no fallback',p.stderr)
        self.proc.terminate();self.proc.communicate(timeout=5)
        args=[str(EXE),'--backend','simulation','--port',str(self.port),'--data',str(self.directory/'data'),'--token-file',str(self.directory/'token')]
        proc=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE);self.addCleanup(self.stop_process,proc)
        for _ in range(80):
            try:self.c=Client(self.base,self.token);break
            except OSError:time.sleep(.025)
        self.c.call('/simulation/inject','POST',{'kind':'reference_position'},error='SIMULATION_DISABLED')
        self.c.call('/simulation/telemetry','POST',{},error='SIMULATION_DISABLED')
        self.assertFalse(self.c.call('/state')['simulation_injection_enabled'])
        self.assertFalse(self.c.call('/state')['position']['valid'])

Boundary.metrics=[]
if __name__=='__main__':
    names=[name for name in Boundary.__dict__ if name.startswith('test_')]
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Boundary(n) for n in names))
    (OUT/'boundary_report.json').write_text(json.dumps({'passed':result.wasSuccessful(),'test_methods':result.testsRun,'metrics':Boundary.metrics,'scope':'host_only'},indent=2))
    sys.exit(not result.wasSuccessful())
