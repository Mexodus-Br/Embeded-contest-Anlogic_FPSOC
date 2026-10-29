"""HTTP and browser E2E through real Service/HardwareBackend, test-only timed board."""
import json, os, socket, subprocess, sys, time, tempfile, urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from partner_support import ROOT,KIT,OUT,compiler,compile_sources
from ps_calibration import parameters
from ps_service import Client

out=OUT/'full-web';out.mkdir(exist_ok=True)
objects=[]
for name in ['rs485_gp','rs485_telem']:
    obj=out/(name+'.o');compile_sources([KIT/'pl_rs485/software'/(name+'.c')],obj,compiler(),cxx=False,extra=['-c']);objects.append(obj)
exe=out/('ps_fake_server.exe' if os.name=='nt' else 'ps_fake_server')
compile_sources([ROOT/'src/ps_core.cpp',KIT/'golden_model/src/model.cpp',*objects,*[ROOT/'src'/f for f in ['ps_backend.cpp','ps_hardware_backend.cpp','ps_runtime.cpp','ps_service.cpp','ps_server.cpp']],ROOT/'tests/ps_fake_board.cpp'],exe,compiler(),includes=[ROOT/'src',ROOT/'third_party',KIT],libraries=['-lws2_32','-lbcrypt'] if os.name=='nt' else ['-pthread'])
with tempfile.TemporaryDirectory(dir=out) as temp:
    data=Path(temp);token='b'*64;(data/'token').write_text(token)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    base='http://127.0.0.1:'+str(port)
    process=subprocess.Popen([str(exe),'--backend','hardware','--port',str(port),'--data',str(data/'state'),'--token-file',str(data/'token')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for n in range(100):
            try:c=Client(base,token);break
            except OSError:time.sleep(.03)
        c.call('/control','POST',{'action':'acquire'})
        def raw(path,body):
            request=urllib.request.Request(base+'/api/v1'+path,data=json.dumps(body).encode(),headers={'Origin':base,'Content-Type':'application/json','X-CSRF-Token':c.csrf},method='POST')
            return json.load(c.open.open(request))
        state=c.call('/state');raw('/hardware/action',dict(action='open',boot_id=state['boot_id']));time.sleep(.1)
        state=c.call('/state');raw('/hardware/action',dict(action='home',boot_id=state['boot_id'],owner_id=state['backend']['owner_id'],cancel_epoch=state['backend']['cancel_epoch'],request_id='test_home',deadline_monotonic_us=str(int(state['monotonic_us'])+1500000)))
        time.sleep(.2);p=parameters();p['fixture'].update(joint_min_deg=[3]*3,joint_max_deg=[86]*3);c.call('/parameters/'+p['id'],'PUT',p)
        assert not c.call('/state')['position']['valid']
        time.sleep(.3);state=c.call('/state');raw('/calibration/verify',dict(boot_id=state['boot_id'],parameter_version=p['id'],home_done_us=state['backend']['home_done_us']))
        state=c.call('/state');assert state['position']['valid'] and not state['simulation']
        config=dict(base=base,token=token,parameters=p,observer_cookie='; '.join(x.name+'='+x.value for x in c.jar))
        c.call('/control','POST',{'action':'release'})
        env=os.environ.copy();env['PS_FULL_WEB_CONFIG']=json.dumps(config)
        result=subprocess.run(['node','tests/ps_full_web.cjs'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
        print(result.stdout+result.stderr);assert result.returncode==0
    finally:
        process.terminate();process.communicate(timeout=5)
print('PASS real HTTP/HardwareBackend browser E2E; timed fake board, no physical devices')
