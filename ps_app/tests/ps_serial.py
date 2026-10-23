"""Local stdin/stdout adapter checks. No serial port or device is opened."""
import json,os,queue,subprocess,threading,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/partner'
exe=OUT/'native'/('ps_control.exe' if os.name=='nt' else 'ps_control')
with tempfile.TemporaryDirectory(prefix='serial-adapter-',dir=OUT) as directory:
    p=subprocess.Popen([str(exe),'simulation',directory],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
    rows=queue.Queue()
    def reader():
        for line in p.stdout:
            rows.put(json.loads(line))
    t=threading.Thread(target=reader,daemon=True);t.start()
    def send(r):
        p.stdin.write(json.dumps(r)+'\n');p.stdin.flush()
    def receive(identity):
        end=time.monotonic()+5
        while time.monotonic()<end:
            row=rows.get(timeout=max(.01,end-time.monotonic()))
            if row.get('request_id')==identity:return row
        raise AssertionError('No correlated response: '+identity)
    try:
        send(dict(request_id='acquire',method='POST',path='/control',body={'action':'acquire'}))
        assert receive('acquire')['result']['you_control']
        for i in range(32):send(dict(request_id='ordinary_'+str(i),method='GET',path='/state'))
        send(dict(request_id='stop',method='POST',path='/stop',body={}))
        stopped=receive('stop');assert stopped['ok'] and stopped['result']['status']=='received'
        send(dict(request_id='state',method='GET',path='/state'))
        state=receive('state');assert state['ok'] and state['result']['simulation'] is True
        assert state['result']['simulation_injection_enabled'] is False
        assert state['result']['position']['valid'] is False
        p.stdin.close();p.wait(timeout=5);assert p.returncode==0,p.stderr.read()
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=5)
        t.join(timeout=1);p.stdout.close();p.stderr.close()
(OUT/'serial_report.json').write_text(json.dumps({'passed':True,'scope':'stdin_stdout_simulation_only','cases':['shared_service_control','bounded_ordinary_queue_STOP','correlated_state','EOF_safe_shutdown']},indent=2))
print('PASS local line adapter control/STOP/correlation/shutdown; no UART')
