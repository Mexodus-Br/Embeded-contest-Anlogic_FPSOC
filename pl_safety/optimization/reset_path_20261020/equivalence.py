"""Compare the pre-change RTL with current RTL; only invalid planner data differ.

Use original independent assertions unchanged, add valid-data/AXI cycle miters
and reset-phase coverage. No log/database hashing and no protected-IP stubs.
"""
import argparse, json, re, shutil, subprocess, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def outputs(text):
    header = re.sub(r'//[^\n]*|/\*.*?\*/', '', text[:text.index(');')], flags=re.S)
    result = {}
    for m in re.finditer(r'\boutput\b(.*?)(?=\b(?:input|output)\b|$)', header, re.S):
        part = re.sub(r'\b(?:wire|reg|signed)\b', '', m[1]).strip()
        w = re.match(r'(\[[^]]+\])', part)
        width = w[1] if w else ''
        if w: part = part[w.end():]
        for n in re.findall(r'\b[A-Za-z_]\w*\b', part): result[n] = width
    return result

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--tag', required=True)
    ap.add_argument('--service-candidate');ap.add_argument('--executor-candidate');ap.add_argument('--source-directory')
    ap.add_argument('--only',choices=['planner','service','registers','continuous','executor']);a = ap.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+', a.tag)
    out = HERE / a.tag; out.mkdir(exist_ok=False)
    all_sources = [p for d in ['pl_motion/rtl', 'pl_rs485/rtl', 'pl_safety/rtl'] for p in (ROOT/d).glob('*.v')]
    modules = {re.search(r'\bmodule\s+(\w+)', re.sub(r'//[^\n]*|/\*.*?\*/', '', p.read_text(), flags=re.S))[1]:p for p in all_sources}
    references = []
    for p in all_sources:
        text = subprocess.check_output(['git','show','07745a8:'+p.relative_to(ROOT).as_posix()],cwd=ROOT).decode('utf-8')
        text = text.replace('\r\n','\n')
        text = re.sub(r'\b('+'|'.join(map(re.escape, modules))+r')\b', lambda m:'ref_'+m[0], text)
        target = out / ('ref_'+p.name); target.write_text(text); references.append(target)
    cases = [('planner', 'pl_motion/tests/tb_motion_planner.v', ['motion_planner']),
             ('continuous', 'pl_motion/tests/tb_continuous_motion.v', ['continuous_motion']),
             ('executor', 'pl_motion/tests/tb_motion_executor.v', ['motion_executor']),
             ('service', 'pl_motion/tests/tb_motion_service.v', ['motion_service']),
             ('registers', 'pl_safety/tests/tb_interlock_regs.v', ['safety_regs','safety_interlock_regs'])]
    if a.only:cases=[c for c in cases if c[0]==a.only]
    compiled_sources=[Path(a.service_candidate).resolve() if a.service_candidate and p.name=='motion_service.v'
                      else Path(a.executor_candidate).resolve() if a.executor_candidate and p.name=='motion_executor.v'
                      else Path(a.source_directory).resolve()/p.name if a.source_directory and (Path(a.source_directory)/p.name).is_file() else p for p in all_sources]
    result = {'passed':False, 'baseline_commit':'07745a8', 'hashes_computed':False, 'cases':[]}
    try:
        for label, bench, instances in cases:
            tb = (ROOT/bench).read_text(); declarations=[]; clones=[]; widths={}
            for module in instances:
                m = re.search(r'\b'+module+r'\s*(?:#\s*\(.*?\)\s*)?(\w+)\s*\(', tb, re.S)
                assert m, module
                end = tb.index(');', m.end())+2
                instance = tb[m.start():end]
                clone = re.sub(r'\b'+module+r'\b', 'ref_'+module, instance, count=1)
                clone = clone[:clone.index(m[1])] + clone[clone.index(m[1]):].replace(m[1], 'reference_'+m[1], 1)
                port_outputs = outputs(modules[module].read_text())
                for port, expr in re.findall(r'\.(\w+)\(([^()]*)\)', instance):
                    if port in port_outputs and re.fullmatch(r'\w+', expr): widths[expr]=port_outputs[port]
                clones.append(clone)
            for name,width in widths.items(): declarations.append(f'wire {width} {name}_ref;')
            for i,clone in enumerate(clones):
                clones[i]=re.sub(r'\.(\w+)\(([^()]*)\)', lambda m:'.'+m[1]+'('+m[2]+('_ref' if m[2] in widths else '')+')', clone)
            compare=[]
            for name in widths:
                condition = 'valid && ' if label=='planner' and name=='data' else ''
                compare.append(f'if({condition}({name} !== {name}_ref))$fatal(1,"{label} mismatch {name}");')
            extra=''
            if label=='service':
                extra='''
 if((dut.execute || dut.dispatch_pending || dut.req_open || dut.req_enable || dut.req_start || dut.req_resume || dut.req_disable) && !dut.command_busy)
  $fatal(1,"command ownership implication");
 if(dut.safety_idle !== reference_dut.safety_idle)$fatal(1,"idle fence equivalence");
'''
            observe='\n'.join(declarations+clones)+'''
integer miter_checks=0;
always @(posedge clk)begin #1;if(rst_n)begin
 miter_checks=miter_checks+1;
'''+ '\n'.join(compare)+extra+'\nend end\n'
            tb=tb.replace('endmodule', observe+'\nendmodule')
            if label=='planner':
                extra_reset='''
 // Reset at every owned arithmetic/held-output phase, including a pulse
 // wholly between clocks. An invalidated record must never become valid.
 for(i=0;i<78;i=i+1)begin
  @(negedge clk);plan_ready=0;cancel=0;rst_n=1;
  base=0;target=64'd7;mask=1;duration=2;sid=64'd1234;seq=i;last=1;
  request;repeat(i)tick;
  @(negedge clk);#1;rst_n=0;#2;
  check(!valid && !reference_dut.plan_valid && !dut.busy && !reference_dut.busy);
  rst_n=1;repeat(80)tick;check(!valid && req_ready);
 end
'''
                tb=tb.replace('  $display("PASS planner', extra_reset+'  $display("PASS planner')
            if label=='registers':
                tb=tb.replace(".live_snapshot(2048'd0)", '.live_snapshot(safety_live)')
                tb=tb.replace('module tb_interlock_regs;', 'module tb_interlock_regs;\nreg [2047:0] safety_live=0;reg [1023:0] expected_live;integer reset_epoch,word_lane;')
                extra_reset='''
 // Every word must read as zero after a between-clock reset even though
 // physical payload storage retains the preceding epoch. Capture all words
 // atomically, mutate live sources under long R stalls, then reset again.
 for(reset_epoch=0;reset_epoch<8;reset_epoch=reset_epoch+1)begin
  @(negedge clk);#1;rst_n=0;#2;rst_n=1;tick;
  for(word_lane=0;word_lane<32;word_lane=word_lane+1)begin
   read(BASE+`SI_SNAPSHOT_BASE+word_lane*4,0,2);check(answer==0,"extension reset masks old data");
  end
  for(word_lane=0;word_lane<64;word_lane=word_lane+1)begin
   read(BASE+`SAF_SNAPSHOT_BASE+word_lane*4,0,2);check(answer==0,"safety reset masks old data");
   safety_live[word_lane*32+:32]=32'h80000000+reset_epoch*256+word_lane;
   if(word_lane<32)live[word_lane*32+:32]=32'h12340000+reset_epoch*256+word_lane;
  end
  expected_live=live;
  write(BASE+`SI_REG_SNAP_REQ,1,15,0,reset_epoch%3,3);
  write(BASE+`SAF_REGISTERS_SNAP_REQ,1,15,0,reset_epoch%3,3);
  live=0;safety_live=0;
  for(word_lane=0;word_lane<32;word_lane=word_lane+1)begin
   read(BASE+`SI_SNAPSHOT_BASE+word_lane*4,0,5);
   check(answer==expected_live[word_lane*32+:32],"extension atomic frozen word");
  end
  for(word_lane=0;word_lane<64;word_lane=word_lane+1)begin
   read(BASE+`SAF_SNAPSHOT_BASE+word_lane*4,0,5);
   check(answer==(word_lane==`SAF_SNAPSHOT_SNAP_ID ? 1:32'h80000000+reset_epoch*256+word_lane),"safety atomic frozen word");
  end
 end
'''
                tb=tb.replace('  $display("PASS interlock_regs', extra_reset+'  $display("PASS interlock_regs')
            tb=tb.replace('$finish;', '$display("MITER_CHECKS %0d",miter_checks);$finish;')
            target=out/(label+'.v');target.write_text(tb)
            top=re.search(r'\bmodule\s+(\w+)',tb)[1]
            includes=[ROOT/p for p in ['pl_interface','pl_rs485/generated','pl_rs485/tests','pl_safety/generated']]
            command=[shutil.which('iverilog'),'-g2005','-s',top,'-o',str(out/(label+'.vvp')),
                     *sum((['-I',str(p)] for p in includes),[]),*map(str,compiled_sources+references+[target])]
            record={'case':label,'passed':False};result['cases'].append(record)
            for phase,cmd in [('compile',command),('simulation',[shutil.which('vvp'),str(out/(label+'.vvp'))])]:
                with (out/(label+'_'+phase+'.log')).open('w') as log:
                    p=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                assert p.returncode==0,(label,phase,p.returncode)
            log=(out/(label+'_simulation.log')).read_text();assert 'PASS' in log and 'MITER_CHECKS' in log
            record.update(passed=True,cycles=int(re.search(r'MITER_CHECKS (\d+)',log)[1]))
            print(record,flush=True)
        result['passed']=True
    except Exception:
        result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
