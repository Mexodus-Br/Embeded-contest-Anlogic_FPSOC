"""HTTP acceptance and failure injection for the loopback-only PS application."""
import copy
import http.client
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/partner'
EXE=OUT/'native'/('ps_server.exe' if os.name=='nt' else 'ps_server')
METRICS=[]
SCHEMA=json.loads((ROOT/'docs/ps-api.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
def validate(name,value):
    Draft202012Validator({'$defs':SCHEMA['$defs'],'$ref':'#/$defs/'+name}).validate(value)
def response_type(path,method,body):
    path=path.split('?')[0]
    exact={'/state':'state','/control':'control','/mode':'mode','/preview':'preview','/preview/cancel':'cancel','/commands':'command','/stop':'stop','/teach':'teach','/jog/start':'jog_started','/jog/refresh':'jog_refreshed','/jog/end':'stop','/telemetry':'telemetry','/simulation/telemetry':'replayed','/logs/boots':'boots','/logs/snapshots':'snapshot','/logs':'page','/parameters':'ids','/tasks':'ids'}
    if path=='/auth':return 'logout' if method=='DELETE' else 'auth'
    if path=='/simulation/inject':return 'log_stats' if body['kind']=='log_burst' else 'applied'
    if path in exact:return exact[path]
    if path.startswith('/parameters/'):return 'saved' if method=='PUT' else 'parameters'
    if path.startswith('/tasks/'):return 'saved' if method=='PUT' else 'task'
    if path.startswith('/commands/'):return 'command'
    if path.startswith('/logs/'):return 'event'
    return exact[path]

class Client:
    def __init__(self,base,token):
        self.base=base;self.csrf='';self.jar=http.cookiejar.CookieJar()
        self.open=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf=self.call('/auth','POST',{'token':token})['csrf']
    def call(self,path,method='GET',body=None,error=None,csrf=True):
        headers={'Origin':self.base,'Content-Type':'application/json'}
        if csrf:headers['X-CSRF-Token']=self.csrf
        req=urllib.request.Request(self.base+'/api/v1'+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers=headers,method=method)
        try:
            with self.open.open(req,timeout=8) as r:
                result=json.loads(r.read())
            if error:raise AssertionError(f'Expected {error}, received {result}')
            validate(response_type(path,method,body),result)
            return result
        except urllib.error.HTTPError as e:
            result=json.loads(e.read())
            validate('failure',result)
            if error:
                assert result['error']['code']==error,result
                return result
            raise AssertionError((e.code,result)) from e

class Service(unittest.TestCase):
    def setUp(self):
        OUT.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='api-test-',dir=OUT)
        self.directory=Path(self.temp.name)
        assert self.directory.resolve().is_relative_to(OUT.resolve())
        self.addCleanup(self.temp.cleanup)
        self.token=uuid.uuid4().hex+uuid.uuid4().hex
        (self.directory/'token').write_text(self.token)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.base=f'http://127.0.0.1:{self.port}'
        self.launch()
        self.c=Client(self.base,self.token)
        self.c.call('/control','POST',{'action':'acquire'})
    def launch(self):
        self.proc=subprocess.Popen([str(EXE),'--backend','simulation','--allow-simulation-injection','true','--port',str(self.port),'--data',str(self.directory.relative_to(ROOT)/'data'),'--token-file',str(self.directory.relative_to(ROOT)/'token')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.addCleanup(self.stop_process,self.proc)
        last_error=None
        for _ in range(80):
            try:
                with urllib.request.urlopen(self.base+'/api/health',timeout=.2) as r:
                    assert json.load(r)['app']=='ps-simulation'
                return
            except (OSError,urllib.error.URLError) as error:
                last_error=error
                if self.proc.poll() is not None:raise AssertionError(self.proc.communicate())
                time.sleep(.03)
        raise AssertionError('Server health failed: '+str(last_error))
    @staticmethod
    def stop_process(process):
        if process.poll() is None:process.terminate()
        process.communicate(timeout=5)
    def tearDown(self):
        self.proc.terminate();self.proc.communicate(timeout=5)
        assert self.directory.resolve().is_relative_to(OUT.resolve())
        self.temp.cleanup()
    def reference(self):self.c.call('/simulation/inject','POST',{'kind':'reference_position'})
    def preview(self,points=None,repeat=None):
        s=self.c.call('/state')
        return self.c.call('/preview','POST',{'schema_version':1,'parameter_version':s['parameter_version'],'start_position_id':s['position']['position_id'],
            'task':{'schema_version':1,'id':'acceptance_task','points':points or [{'xyz_mm':[5,0,-140]}],'repeat':repeat or {'mode':'finite','count':'1'}}})
    def command(self,p):
        s=self.c.call('/state');return {'boot_id':s['boot_id'],'client_command_id':uuid.uuid4().hex,'preview_id':p['preview_id'],'deadline_monotonic_us':str(int(s['monotonic_us'])+2000000)}
    def idle(self,timeout=3):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            s=self.c.call('/state')
            if s['phase']=='idle':return s
            time.sleep(.01)
        raise AssertionError(s)
    def test_authentication_scope_and_csrf(self):
        self.c.call('/stop','POST',{},error='AUTH',csrf=False)
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(self.base+'/api/v1/state')
        self.c.call('/auth','POST',{'token':'not-the-token'},error='AUTH')
        self.c.call('/logs/export?path=../../.cache/ps-token',error='FORMAT')
        self.c.call('/tasks/..%2f..%2fsecret',error='FORMAT')
        other=Client(self.base,self.token)
        other.call('/control','POST',{'action':'acquire'},error='CONTROL_BUSY')
        # Any authenticated observer retains independent STOP.
        self.assertEqual(other.call('/stop','POST',{})['status'],'received')
    def test_preview_unknown_invalid_stale_and_expiry(self):
        before=self.c.call('/state');p=self.preview();self.assertFalse(p['executable']);self.assertIsNone(self.c.call('/state')['position']['xyz_mm'])
        self.c.call('/commands','POST',self.command(p),error='POSITION_UNKNOWN')
        self.reference();before=self.c.call('/state');p=self.preview();after=self.c.call('/state')
        self.assertEqual(before['position'],after['position']);self.assertEqual(after['phase'],'idle')
        command=self.command(p);self.c.call('/preview/cancel','POST',{});self.c.call('/commands','POST',command,error='PREVIEW_STALE')
        p=self.preview();command=self.command(p);command['deadline_monotonic_us']='1';self.c.call('/commands','POST',command,error='EXPIRED')
        command=self.command(p);command['boot_id']='old';self.c.call('/commands','POST',command,error='BOOT_MISMATCH')
        s=self.c.call('/state')
        self.c.call('/preview','POST',{'parameter_version':s['parameter_version'],'start_position_id':s['position']['position_id'],'task':{'points':[{'xyz_mm':[5,0,-140],'duration_us':'100'}]}},error='DURATION_INSUFFICIENT')
        self.assertIsNone(self.c.call('/state')['preview_id'])
    def test_explicit_run_idempotency_and_autonomy(self):
        self.reference();p=self.preview([{'xyz_mm':[5,0,-140],'duration_us':'600000'}]);cmd=self.command(p)
        self.assertEqual(self.c.call('/commands','POST',cmd)['status'],'submitted')
        retry=self.c.call('/commands','POST',cmd);self.assertEqual(retry['command_id'],cmd['client_command_id'])
        changed={**cmd,'preview_id':'different'};self.c.call('/commands','POST',changed,error='ID_CONFLICT')
        s=self.c.call('/state');self.c.call('/preview','POST',{'parameter_version':s['parameter_version'],'start_position_id':s['position']['position_id'],'task':{'points':[{'xyz_mm':[0,0,-140]}]}},error='BUSY')
        # No browser or subsequent point supply while accepted autonomous task runs.
        time.sleep(.75);s=self.c.call('/state');self.assertEqual(s['phase'],'idle');self.assertEqual(s['command']['status'],'completed')
        self.assertEqual(s['position']['xyz_mm'],[5,0,-140]);self.assertEqual(self.c.call('/commands','POST',cmd)['status'],'completed')
    def test_rejected_identity_and_command_task_log_correlation(self):
        p=self.preview();cmd=self.command(p)
        first=self.c.call('/commands','POST',cmd,error='POSITION_UNKNOWN')
        self.reference()
        self.assertEqual(first,self.c.call('/commands','POST',cmd,error='POSITION_UNKNOWN'))
        self.assertEqual(self.c.call('/commands/'+cmd['client_command_id'])['status'],'failed')
        changed=self.command(self.preview());changed['client_command_id']=cmd['client_command_id']
        self.c.call('/commands','POST',changed,error='ID_CONFLICT')
        changed['client_command_id']=uuid.uuid4().hex;self.c.call('/commands','POST',changed);self.idle()
        snap=self.c.call('/logs/snapshots','POST',{'command_id':changed['client_command_id'],'task_id':'acceptance_task'})
        rows=self.c.call('/logs?snapshot='+snap['snapshot_id'])['events']
        self.assertTrue(rows);self.assertTrue(all(r['task_id']=='acceptance_task' for r in rows))
        if not {'validated','submitted','running','completed'}.issubset({r['event'] for r in rows}):
            # The nonblocking logger can drop on queue saturation OR lock contention;
            # partial history must explicitly disclose loss, never claim completeness.
            self.assertTrue(snap['gaps']);self.assertGreater(int(snap['dropped']),0)
    def test_task_round_trip_and_running_parameter_snapshot(self):
        self.reference()
        task={'schema_version':1,'id':'round_trip','parameter_version':'host_demo_v1','points':[{'xyz_mm':[5,0,-140],'duration_us':'600000','dwell_us':'100000'},{'xyz_mm':[0,0,-140],'duration_us':'700000','dwell_us':'20000'}],'repeat':{'mode':'finite','count':'2'}}
        self.c.call('/tasks/round_trip','PUT',task);self.assertEqual(self.c.call('/tasks/round_trip'),task)
        p=self.preview(task['points'],task['repeat']);cmd=self.command(p);self.c.call('/commands','POST',cmd)
        params=self.c.call('/parameters/host_demo_v1');new=copy.deepcopy(params);new['id']='during_run';new['fixture']['speed_mm_s']=1
        self.c.call('/parameters/during_run','PUT',new)
        s=self.idle(timeout=4);self.assertEqual(s['command']['status'],'completed');self.assertFalse(s['position']['valid'])
        self.c.call('/parameters/host_demo_v1','PUT',params);s=self.c.call('/state');self.assertTrue(s['position']['valid']);self.assertEqual(s['position']['xyz_mm'],[0,0,-140])
        params['fixture']['speed_mm_s']=2;self.c.call('/parameters/host_demo_v1','PUT',params,error='VERSION_CONFLICT')
        # A saved task must explicitly match the selected parameter snapshot.
        self.c.call('/parameters/during_run','PUT',new);s=self.c.call('/state')
        self.c.call('/preview','POST',{'parameter_version':'during_run','start_position_id':s['position']['position_id'],'task':task},error='PARAMETER_MISMATCH')
    def test_storage_failure_preserves_documents_and_stop_during_long_plan(self):
        task={'id':'saved','points':[{'xyz_mm':[5,0,-140]}]}
        self.c.call('/tasks/saved','PUT',task);before=(self.directory/'data/tasks/saved.json').read_bytes()
        task['points'][0]['xyz_mm'][0]=6;self.c.call('/tasks/saved','PUT',task,error='VERSION_CONFLICT')
        self.assertEqual(before,(self.directory/'data/tasks/saved.json').read_bytes())
        # A file at a required directory path produces a real local filesystem failure.
        (self.directory/'data/parameters').write_text('blocked directory fixture')
        params=self.c.call('/parameters/host_demo_v1');params['id']='cannot_save'
        self.c.call('/parameters/cannot_save','PUT',params,error='STORAGE')
        self.assertEqual(self.c.call('/state')['parameter_version'],'host_demo_v1')
        self.reference();s=self.c.call('/state')
        request={'parameter_version':s['parameter_version'],'start_position_id':s['position']['position_id'],'task':{'points':[{'xyz_mm':[5 if i%2==0 else 0,0,-140]} for i in range(1000)]}}
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.c.call,'/preview','POST',request,error='PREVIEW_STALE');time.sleep(.03)
            begin=time.perf_counter();self.c.call('/stop','POST',{});self.idle();elapsed=time.perf_counter()-begin
            METRICS.append({'case':'stop_during_long_planning','seconds':elapsed});self.assertLess(elapsed,.1);future.result(timeout=8)
    def test_sse_reconnect_has_boot_identity_and_no_command_replay(self):
        cookie='; '.join(c.name+'='+c.value for c in self.c.jar)
        def read_events(last):
            con=http.client.HTTPConnection('127.0.0.1',self.port,timeout=2)
            con.request('GET','/api/v1/events',headers={'Cookie':cookie,'Last-Event-ID':last})
            response=con.getresponse();self.assertEqual(response.status,200);lines=[]
            for _ in range(100):
                line=response.fp.readline().decode();lines.append(line)
                if line.startswith('event: state'):
                    lines.append(response.fp.readline().decode());break
            response.close();con.close();return ''.join(lines)
        self.assertIn('boot_changed',read_events('previous_boot:1'))
        s=self.c.call('/state');events=read_events(s['boot_id']+':18446744073709551615')
        self.assertIn('events_missing',events);self.assertIn('id: '+s['boot_id']+':',events)
        self.assertEqual(self.c.call('/state')['phase'],'idle');self.assertIsNone(self.c.call('/state')['command'])
    def test_revoking_control_stops_manual_but_keeps_autonomous_task(self):
        self.reference();p=self.preview([{'xyz_mm':[5,0,-140],'duration_us':'600000'}]);self.c.call('/commands','POST',self.command(p))
        self.c.call('/auth','DELETE',{});self.c=Client(self.base,self.token)
        self.assertFalse(self.c.call('/state')['control_owned']);self.assertEqual(self.idle()['command']['status'],'completed')
        self.c.call('/control','POST',{'action':'acquire'});self.c.call('/mode','POST',{'mode':'manual'});s=self.c.call('/state')
        self.c.call('/jog/start','POST',{'boot_id':s['boot_id'],'jog_id':uuid.uuid4().hex,'axis':'y','sign':1,'speed_mm_s':5,'refresh_seq':'0','stop_epoch':s['stop_epoch'],'deadline_monotonic_us':str(int(s['monotonic_us'])+2000000)})
        self.c.call('/auth','DELETE',{});self.c=Client(self.base,self.token);self.idle()
        self.assertFalse(self.c.call('/state')['control_owned'])
    def test_stop_cancels_infinite_repeat_and_failure(self):
        self.reference();p=self.preview([{'xyz_mm':[5,0,-140],'duration_us':'600000'},{'xyz_mm':[0,0,-140],'duration_us':'600000'}],{'mode':'until_stopped'})
        cmd=self.command(p);self.c.call('/commands','POST',cmd);time.sleep(.1)
        start=time.perf_counter();self.c.call('/stop','POST',{});s=self.idle();elapsed=time.perf_counter()-start
        METRICS.append({'case':'stop_infinite_task','seconds':elapsed});self.assertLess(elapsed,.1)
        self.assertEqual(s['command']['status'],'cancelled');position=s['position']['xyz_mm'];time.sleep(.15);self.assertEqual(position,self.c.call('/state')['position']['xyz_mm'])
        self.c.call('/simulation/inject','POST',{'kind':'stop_failure'});self.c.call('/stop','POST',{});time.sleep(.05)
        self.assertEqual(self.c.call('/state')['phase'],'fault');self.assertFalse(self.c.call('/state')['position']['valid'])
        self.c.call('/simulation/inject','POST',{'kind':'clear_stop_failure'});self.c.call('/stop','POST',{});self.idle()
    def test_manual_timeout_refresh_order_and_replay(self):
        self.reference();self.c.call('/mode','POST',{'mode':'manual'});s=self.c.call('/state')
        j={'boot_id':s['boot_id'],'jog_id':uuid.uuid4().hex,'axis':'x','sign':1,'speed_mm_s':5,'refresh_seq':'0','stop_epoch':s['stop_epoch'],'deadline_monotonic_us':str(int(s['monotonic_us'])+2000000)}
        self.c.call('/jog/start','POST',j);time.sleep(.1)
        self.c.call('/jog/refresh','POST',{'boot_id':s['boot_id'],'jog_id':j['jog_id'],'refresh_seq':'0'},error='STALE_INPUT')
        time.sleep(.32);now=self.idle();self.assertGreater(now['position']['xyz_mm'][0],0)
        self.c.call('/jog/refresh','POST',{'boot_id':s['boot_id'],'jog_id':j['jog_id'],'refresh_seq':'1'},error='STALE_INPUT')
        j.update(stop_epoch=now['stop_epoch'],deadline_monotonic_us=str(int(now['monotonic_us'])+2000000));self.c.call('/jog/start','POST',j,error='STALE_INPUT')
        # Delayed pointer-down arriving after pointer-up STOP must never start.
        j['jog_id']=uuid.uuid4().hex;self.c.call('/stop','POST',{});self.idle();self.c.call('/jog/start','POST',j,error='STALE_INPUT')
    def test_parameters_and_tasks_are_versioned_not_executed(self):
        self.reference();p=self.preview();s=self.c.call('/state');params=self.c.call('/parameters/'+s['parameter_version']);params['id']='parameters_2'
        cmd=self.command(p);self.c.call('/parameters/parameters_2','PUT',params);self.c.call('/commands','POST',cmd,error='PREVIEW_STALE')
        params['fixture']['speed_mm_s']=5;self.c.call('/parameters/parameters_2','PUT',params,error='VERSION_CONFLICT')
        task={'schema_version':1,'id':'test_task','points':[{'xyz_mm':[5,0,-140]}],'repeat':{'mode':'finite','count':'2'}}
        self.c.call('/tasks/test_task','PUT',task);loaded=self.c.call('/tasks/test_task');self.assertEqual(loaded['parameter_version'],'parameters_2');self.assertEqual(self.c.call('/state')['phase'],'idle')
        self.c.call('/teach','POST',{},error='POSITION_UNKNOWN');self.reference();self.assertEqual(self.c.call('/teach','POST',{})['source'],'simulation')
    def test_telemetry_replay_preserves_source_and_staleness(self):
        self.c.call('/simulation/telemetry','POST',{});t=self.c.call('/telemetry');self.assertEqual(len(t['history']),17);self.assertEqual(sum(r['data_valid'] for r in t['history']),16)
        self.assertIsNone(t['xyz_feedback']);self.assertGreater(int(t['missing_serials']),0)
        self.assertTrue(any(not r['current_generation'] and r['stale'] for r in t['latest'].values()))
        for r in t['history']:
            if not r['data_valid']:self.assertIsNone(r['value'])
            if r['query']==0x33:self.assertEqual(r['kind'],'command_pulses')
        time.sleep(.55);self.assertTrue(self.c.call('/telemetry')['stale'])
    def test_logs_snapshot_content_faults_rotation_and_stop(self):
        self.c.call('/simulation/inject','POST',{'kind':'logs','pause_log_writer':True})
        self.c.call('/simulation/inject','POST',{'kind':'log_burst','count':'1200'})
        self.assertGreater(int(self.c.call('/state')['logs']['dropped']),0)
        snap=self.c.call('/logs/snapshots','POST',{'component':'simulation'});page=self.c.call('/logs?snapshot='+snap['snapshot_id']+'&limit=100')
        self.assertTrue(snap['gaps']);self.assertEqual(len(page['events']),100)
        self.assertEqual(self.c.call('/logs/'+page['events'][0]['event_id']),page['events'][0])
        self.c.call('/logs?snapshot='+snap['snapshot_id']+'&cursor=wrong:100',error='FORMAT')
        url=self.base+'/api/v1/logs/export?snapshot='+snap['snapshot_id']
        export=self.c.open.open(url).read();lines=[json.loads(s) for s in export.splitlines()]
        self.assertEqual(lines[0]['count'],len(lines)-1);self.assertEqual(lines[1]['details']['text'],'中文日志\n第二行')
        self.c.call('/stop','POST',{});self.idle();self.assertEqual(self.c.open.open(url).read(),export)
        self.c.call('/simulation/inject','POST',{'kind':'logs','disk_failure':True})
        time.sleep(.1);self.assertGreater(int(self.c.call('/state')['logs']['write_errors']),0)
        self.c.call('/simulation/inject','POST',{'kind':'logs'})
        log=self.directory/'data/logs/events.jsonl';log.parent.mkdir(parents=True,exist_ok=True)
        # Controlled fixture simulates a segment reaching its rotation boundary.
        with log.open('ab') as f:f.write((b'{"fixture":"rotation"}\n')*200000)
        self.c.call('/simulation/inject','POST',{'kind':'log_burst','count':'5'});time.sleep(.1)
        self.assertTrue((log.parent/'events.1.jsonl').exists())
        # Keep a download socket unconsumed while issuing STOP on another connection.
        slow=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        cookie='; '.join(c.name+'='+c.value for c in self.c.jar)
        slow.request('GET','/api/v1/logs/export?snapshot='+snap['snapshot_id'],headers={'Cookie':cookie});response=slow.getresponse();self.assertEqual(response.status,200)
        start=time.perf_counter();self.c.call('/stop','POST',{});self.idle();elapsed=time.perf_counter()-start;response.close();slow.close()
        METRICS.append({'case':'stop_during_slow_log_download','seconds':elapsed});self.assertLess(elapsed,.1)
        for _ in range(3):self.c.call('/logs/snapshots','POST',{})
        self.c.call('/logs/snapshots','POST',{},error='SNAPSHOT_LIMIT')
    def test_restart_never_replays_or_fabricates_position(self):
        self.reference();p=self.preview([{'xyz_mm':[5,0,-140],'duration_us':'2000000'}]);cmd=self.command(p);self.c.call('/commands','POST',cmd)
        self.proc.terminate();self.proc.communicate(timeout=5);self.launch();self.c=Client(self.base,self.token)
        s=self.c.call('/state');self.assertEqual(s['phase'],'idle');self.assertFalse(s['position']['valid']);self.assertEqual(s['recovery']['status'],'unknown')
        self.c.call('/commands','POST',cmd,error='BOOT_MISMATCH');self.c.call('/stop','POST',{});self.idle()

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Service);result=unittest.TextTestRunner(verbosity=2).run(suite)
    (OUT/'service_report.json').write_text(json.dumps({'passed':result.wasSuccessful(),'test_methods':result.testsRun,'stop_metrics':METRICS,'scope':'host_simulation_only'},indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
