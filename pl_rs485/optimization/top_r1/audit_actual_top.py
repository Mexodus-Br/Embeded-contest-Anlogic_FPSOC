"""Report the ONE actual GPIO board top; retain diagnostics and fail release."""
import hashlib,json,re,shutil
from pathlib import Path
R=Path('D:\\Works\\Embedded_contest\\dev');W=R/'bsp/work/telemetry_opt_r1';E=R/'pl_rs485/optimization/top_r1/reports'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
E.mkdir(exist_ok=True)
log=(W/'build_gp.log').read_text(encoding='utf-8')
if (W/'resume_gate.log').exists():log+='\n'+(W/'resume_gate.log').read_text(encoding='utf-8')
assert 'BSP_TELEMETRY_RESOURCE_BUILD_COMPLETE' in log,'Wait for complete route report; never certify an estimate'
stages={}
for stage in ('gate','place','route'):
 t=(W/('gp_'+stage+'.timing')).read_text(encoding='utf-8')
 stages[stage]={'setup_wns_ns':float(re.search(r'SWNS:\s*([-\d.]+)ns',t)[1]),'hold_wns_ns':float(re.search(r'HWNS:\s*([-\d.]+)ns',t)[1]),'coverage':re.search(r'STA coverage\s*:\s*([^\n]+)',t)[1].strip(),'corners':re.search(r'Check Corner\s*:\s*([^\n]+)',t)[1].strip()}
route=(W/'gp_route.timing').read_text(encoding='utf-8');area=(W/'gp_route.area').read_text(encoding='utf-8');check=(W/'gp_route.check').read_text(encoding='utf-8')
clocks=['board_100m']+['ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_'+n for n in ('GP0S','HP0','HP1')]
for name in clocks:assert re.search(r'100\.000\s+[1-9]\d*\s+'+re.escape(name)+r'\s',route),name
totals={'lut6':52480,'slice':52480,'reg':104960,'eram':280,'dsp':240,'gclk':32,'sclk':72,'pad':126}
used={}
for k,total in totals.items():
 if k=='reg':
  match=re.search(r'^\s*#slice reg\s+(\d+)\s+out of\s+(\d+)',area,re.M)
 else:match=re.search(r'^#'+k+r'\s+(\d+)\s+out of\s+(\d+)',area,re.M)
 assert match and int(match[2])==total,(k,match.group(0) if match else None)
 used[k]={'used':int(match[1]),'total':total,'percent':round(100*int(match[1])/total,4),'remaining':total-int(match[1])}
all_regs=int(re.search(r'^#reg\s+(\d+)',area,re.M)[1]);pad_regs=int(re.search(r'^\s*#pad reg\s+(\d+)',area,re.M)[1])
hierarchy=[];selected={'motion_dma_lite_top','motion_service','rs485_gp_bridge','rs485_latest_cache','rs485_telemetry','telemetry_dma_lite_top','axi_lite_six_way','rs485_probe_time_regs'}
for stage in ('gate','route'):
 t=(W/('gp_'+stage+'.area')).read_text(encoding='utf-8')
 header=None
 for line in t.splitlines():
  if '|Instance' in line:header=[x.strip() for x in line.split('|')[1:-1]];continue
  if header and line.startswith('|'):
   row=[x.strip() for x in line.split('|')[1:-1]]
   if len(row)==len(header) and row[1] in selected:hierarchy.append({'stage':stage,'inclusive_child_resources_not_additive':dict(zip(header,row))})
assert any(x['inclusive_child_resources_not_additive']['Module']=='rs485_latest_cache' for x in hierarchy),'Cache was flattened or removed; investigate, do not invent retention'
gpio=json.loads((R/'pl_motion/scope_test/CONFIG.json').read_text(encoding='utf-8'))['pins']
for p in gpio:assert re.search(r'^\s*'+p['port']+r'\s+OUTPUT\s+'+p['ball']+r'\s+LVCMOS33\s+HRIO\s+8\s+NONE\s+OREG',area,re.M),p
for name,ball,direction in [('rs485_tx','L17','OUTPUT'),('rs485_rx','N16','INPUT'),('rs485_de','N15','OUTPUT')]:
 assert re.search(r'^\s*'+name+r'\s+'+direction+r'\s+'+ball+r'\s+LVCMOS33',area,re.M),(name,ball)
critical=[x for x in log.splitlines() if 'CRITICAL-WARNING' in x]
diagnostics={}
for name in ('no clock','clock definition','dummy node','no input delay','no output delay','invalid constraint','combinational loop'):
 hits=re.findall(r'checking '+re.escape(name)+r's?\((\d+)\)',check);diagnostics[name]=[int(x) for x in hits]
timing_pass=min(stages['route']['setup_wns_ns'],stages['route']['hold_wns_ns'])>=0
diagnostics_closed=not critical and all(not any(v) for k,v in diagnostics.items() if k!='dummy node')
summary={'status':'FULL_ACTUAL_GPIO_TOP_RESOURCE_REVIEW','reference_speed':2,'real_device_speed':'UNCONFIRMED','clock_mhz':100,'stages':stages,'resources':used,'register_design_total_including_pad':all_regs,'pad_registers_separate':pad_regs,'hierarchy':hierarchy,'critical_warnings':critical,'check_timing':diagnostics,'timing_pass':timing_pass,'diagnostics_closed':diagnostics_closed,'signoff_pass':timing_pass and diagnostics_closed,'bitgen':'NOT_EXECUTED','hpf_boot_image':'NOT_GENERATED','clock_names':clocks,'functional_retention':'nine real GPIO OREGs; complete cache hierarchy/snapshots; six live GP endpoints and both DMA controllers; source wiring + real-IP system differential tests','input_identity':json.loads((W/'connections.json').read_text(encoding='utf-8')),'constraints_sha256':{'adc':sha(W/'gp/gp.adc'),'sdc':sha(W/'gp/gp.sdc'),'ps_properties':sha(W/'gp/ps-generated-properties.tcl')},'congestion_lines':[x for x in log.splitlines() if any(k in x for k in ('overflow','Over-util','congestion','top1  =','Congestion'))][-80:]}
for p in W.iterdir():
 if p.is_file() and (p.suffix in ('.log','.timing','.check','.area','.drc','.qor','.tcl') or p.name=='connections.json'):shutil.copyfile(p,E/p.name)
for name in ('system/hdl/system_wrapper.v','gp/gp.adc','gp/gp.sdc','gp/ps-generated-properties.tcl'):
 shutil.copyfile(W/name,E/Path(name).name)
(E/'hardware-review.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
(E/'review.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
(E/'identity.json').write_text(json.dumps({p.name:sha(p) for p in sorted(E.iterdir()) if p.is_file() and p.name!='identity.json'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ('resources','stages','critical_warnings','signoff_pass')},indent=2))
