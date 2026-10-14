"""Freeze this independent HP1 delivery against its actual simulation/TD inputs."""
import hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
S=R/'pl_rs485';D=R/'pl_dma'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def old(n):return subprocess.check_output(['git','show','698834c:'+n],cwd=R).decode().replace('\r\n','\n')
def check_hashes(base,m):
 for n,h in m.items():
  p=base/n.replace('\\','/')
  if sha(p)!=h:raise RuntimeError('stale evidence '+str(p))
def expanded(p):
 t=p.read_text().replace('`include "generated/interface_defs.vh"',(R/'pl_interface/generated/interface_defs.vh').read_text())
 return re.sub(r'`include "([^"]+)"',lambda m:(S/'generated'/m[1]).read_text(),t)
def main():
 for p in ['pl_interface/generate.py','pl_rs485/tools/generate_gp.py','pl_rs485/tools/generate_telem.py','pl_dma/generate_telemetry.py']:
  subprocess.run(['python',str(R/p),'--check'],check=True)
 schema=load(R/'pl_interface/schema.json');retained=dict(schema);retained.pop('rs485_telemetry')
 if retained!=json.loads(old('pl_interface/schema.json')):raise RuntimeError('old ABI changed')
 baseline=load(S/'evidence/identity_multirate.json')['source_sha256']
 for n in ['schema.json','rate_design.json','rtl/rs485_master.v','rtl/uart_tx.v','rtl/uart_rx.v','rtl/record_fifo.v','rtl/rs485_transaction.v','rtl/div_u64_u32.v']:
  if sha(S/n)!=baseline[n]:raise RuntimeError('retained source '+n)
 mr=(S/'rtl/rs485_multirate.v').read_text().replace(' `include "rate_defs.vh"\n','')
 if mr!=old('pl_rs485/rtl/rs485_multirate.v').replace(' `include "rate_defs.vh"\n',''):raise RuntimeError('scheduler changed')
 gp=(S/'rtl/rs485_gp_regs.v').read_text().replace(' input wire [7999:0] observe_tasks,input wire [1279:0] observe_nodes,\n output wire [31:0] observe_generation);',' input wire [7999:0] observe_tasks,input wire [1279:0] observe_nodes);').replace(' assign observe_generation=generation;\n','')
 if gp!=old('pl_rs485/rtl/rs485_gp_regs.v'):raise RuntimeError('old GP state changed')
 bridge=(S/'rtl/rs485_gp_bridge.v').read_text().replace('output wire [31:0] s_rdata,\n output wire completed_valid,output wire [255:0] completed_raw,output wire [31:0] completed_generation,completed_revision,\n output wire [159:0] current_periods,output wire [4:0] current_mask);','output wire [31:0] s_rdata);')
 bridge=bridge.replace('assign completed_valid=push;assign completed_raw=push_data;assign completed_revision=revision;\nassign current_periods=ap;assign current_mask=am;\n','').replace('.observe_generation(completed_generation),','')
 if bridge!=old('pl_rs485/rtl/rs485_gp_bridge.v'):raise RuntimeError('old GP bridge changed beyond observations')
 probe=(D/'rtl/rs485_probe_time_regs.v').read_text().replace('module rs485_probe_time_regs(','module gp_control_regs(')
 probe=probe.replace('    output wire [63:0] shared_time_us,\n','').replace('    assign shared_time_us=timestamp;\n','')
 if probe!=(R/'pl_motion/rtl/gp_control_regs.v').read_text():raise RuntimeError('time export exceeds observation')
 simulations={}
 rs_names=['telemetry_unit_final','telem_results_final','telem_parse_final','telem_software_final','telem_irq_final','sim_dma_gp_final','sim_dma_legacy_final','sim_dma_multirate_final','software_dma_final']
 for name in rs_names:
  m=load(S/'evidence'/name/'manifest.json');check_hashes(S,m['source_sha256'])
  if not m.get('passed'):raise RuntimeError('simulation did not pass '+name)
  simulations[name]=m['passed']
 for name in ['telemetry_ip_r2','telemetry_system_final']:
  m=load(D/'reports'/name/'result.json')
  if m['status']!='PASS':raise RuntimeError(name)
  check_hashes(R,m.get('source_sha256',{}))
  for lib in m['real_ip']['libraries'].values():
   # Staged IP is an exact copy of the installed protected vendor source.
   if sha(Path(lib['staged']))!=lib['sha256']:raise RuntimeError('IP identity')
   if sha(Path(lib['source']))!=lib['sha256']:raise RuntimeError('installed IP identity')
  simulations[name]=m['result']
 if not load(D/'reports/telemetry_regression_r2/result.json')['passed']:raise RuntimeError('regressions')
 sw=load(S/'evidence/telem_software_final/manifest.json')
 if sha(S/'evidence/telemetry_unit_final/frames.hex')!=sw['vectors_sha256']:raise RuntimeError('software vectors')
 components={'parse_r1':['pl_rs485/rtl/rs485_light_parse.v'],
 'cache_packed':['pl_rs485/rtl/rs485_latest_cache.v','pl_rs485/rtl/rs485_light_parse.v'],
 'packet_final':['pl_rs485/rtl/rs485_telemetry.v'],
 'dma_r1':['pl_dma/rtl/telemetry_dma_lite_top.v','pl_dma/rtl/telemetry_dma_guard.v']}
 timing={};diagnostics={}
 for name,deps in components.items():
  e=D/'reports'/('telem_'+name);b=D/'build'/('telem_'+name);m=load(e/'summary.json')
  hashes={k.replace('\\','/'):v for k,v in m['source_sha256'].items()}
  for n in deps:
   if sha(R/n)!=hashes[n]:raise RuntimeError('TD core differs '+n)
   if (b/Path(n).name).read_text()!=expanded(R/n):raise RuntimeError('expanded TD source '+n)
  if sha(e/'top.v')!=m['fixture_sha256'] or sha(e/'clock.sdc')!=m['constraint_sha256']:raise RuntimeError('fixture changed')
  if m['clock_MHz']!=100 or any(v<0 for v in m['stages']['route'].values()):raise RuntimeError('timing failed '+name)
  timing[name]=m['stages']
  diagnostics[name]=[s for s in (e/'run.log').read_text().splitlines() if 'CRITICAL-WARNING' in s]
 soc=load(D/'reports/telemetry_soc_final/summary.json');check_hashes(R,soc['inputs'])
 if not soc['timing_pass'] or soc['clock_period_ns']!=10:raise RuntimeError('SoC timing')
 final_timing=(D/'reports/telemetry_soc_final/route.timing').read_text()
 for clock_name in soc['actual_model_clock_names']:
  if clock_name not in final_timing:raise RuntimeError('actual STA clock '+clock_name)
 for n in soc['inputs']:
  if (D/'build/telemetry_soc_final'/Path(n).name).read_text()!=expanded(R/n):raise RuntimeError('SoC expansion '+n)
 audit=load(D/'reports/telemetry_candidate/audit.json')
 if sha(Path(audit['generated_raw']))!=audit['raw_sha256']:raise RuntimeError('PS identity')
 if sha(Path(soc['ps_properties_source']))!=soc['ps_properties_source_sha256']:raise RuntimeError('BSP PS properties changed')
 for n in ['pl_dma/generate_top.py','pl_dma/generate_shared.py','pl_dma/generate_motion.py','pl_dma/prepare_ip.py']:
  if (R/n).read_text()!=old(n):raise RuntimeError('old generator changed '+n)
 # Freeze sources and reports, excluding generated binaries/databases and this identity itself.
 sources=[]
 for root in [S,D,R/'pl_interface']:
  sources.extend(p for p in root.glob('*') if p.is_file() and (p.suffix in ['.py','.md','.json'] or p.name=='.gitattributes'))
  for folder in ['rtl','generated','software','tests','tools','tb']:
   sources.extend(p for p in (root/folder).glob('*') if p.is_file() and p.suffix in ['.v','.vh','.c','.h','.py','.md','.json'])
 evidence=[]
 for name in rs_names:
  evidence.extend(p for p in (S/'evidence'/name).glob('*') if p.suffix not in ['.exe','.vvp'])
 evidence.append(S/'evidence/TELEMETRY_FAILURES.md')
 for name in ['telemetry_candidate','telemetry_ip_r2','telemetry_system_final','telemetry_regression_r2','telemetry_failures','telemetry_soc_final']+['telem_'+n for n in components]:
  evidence.extend(p for p in (D/'reports'/name).rglob('*') if p.is_file())
 identity={'identity':'rs485-telemetry-hp1-v1','baseline_commit':'698834c','gp_baseline_commit':'7a0d479',
 'canonical_schema_sha256':sha(R/'pl_interface/schema.json'),
 'baseline_vendor_evidence_sha256_lf':hashlib.sha256((R/'pl_interface/vendor_evidence.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
 'vendor_libraries':load(D/'reports/telemetry_system_final/result.json')['real_ip']['libraries'],
 'ps_raw_sha256':audit['raw_sha256'],'ps_properties_sha256':soc['ps_properties_source_sha256'],
 'source_sha256':{p.relative_to(R).as_posix():sha(p) for p in sorted(set(sources)) if p!=R/'pl_interface/vendor_evidence.json'},
 'evidence_sha256':{p.relative_to(R).as_posix():sha(p) for p in sorted(set(evidence))},
 'simulations':simulations,'timing':timing,'soc_route':soc['stages']['route'],'soc_resources':soc['route_resources'],
 'effective_s2mm_parameters':schema['rs485_telemetry']['dma']['parameters'],
 'critical_warnings':dict(diagnostics,soc=soc['critical_warnings']),
 'diagnostics_closed':soc['diagnostics_closed'],'physical_signoff_pass':soc['signoff_pass'],
 'retained_schema_equal':True,'collector_logic_unchanged':True,'old_gp_observation_only_delta':True,'single_system_time_observation_only':True,
 'board_integrated':False,'board_accepted':False}
 (S/'evidence/identity_telemetry.json').write_bytes((json.dumps(identity,indent=2,ensure_ascii=False)+'\n').encode())
 print('PASS independent telemetry identity / evidence / compatibility freeze')
if __name__=='__main__':main()
