"""Isolated real-PS GP0+HP0 reference, not a BSP/HPF/boot-image replacement."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from prepare_ip import ROOT,TD,prepare,digest
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',default='final');ap.add_argument('--report-only',action='store_true');a=ap.parse_args()
 if not re.fullmatch('[A-Za-z0-9_-]+',a.tag):raise ValueError('invalid build tag')
 b=ROOT/('build/motion_soc_'+a.tag);b.mkdir(parents=True,exist_ok=True);ip=prepare()
 audit=json.loads((ROOT/'HP0_PORTS.json').read_text());raw=Path(audit['generated_raw'])
 if digest(raw)!=audit['raw_sha256']:raise RuntimeError('PS audit differs')
 text=raw.read_text();parameters=dict(re.findall(r'parameter\s+(\w+)\s*=\s*(\d+)',text));ports={}
 for d,w,n in re.findall(r'^\s*(input|output)\s+(?:\[([^]]+):0\]\s*)?(\w+)\s*[,)]',text,re.M):
  expr=w
  for key,value in parameters.items():expr=expr.replace(key,value)
  ports[n]=(d,int(eval(expr,{'__builtins__':{}}))+1 if expr else 1)
 module=re.search(r'\bmodule\s+(\w+)',text)[1]
 lines=['// Isolated generated PS reference; no bitstream/HPF/FSBL deployment.',
        'module motion_soc_reference(input wire clk_100m);','wire gp0_aclk,hp0_aclk,arst_n,control_rst_n,unused_p2f_clk0;wire [15:0] f2p_irq;']
 ps=[];pl=['.clk_100m(clk_100m)','.arst_n(arst_n)','.gp0_aclk(gp0_aclk)','.hp0_aclk(hp0_aclk)','.control_rst_n(control_rst_n)','.f2p_irq(f2p_irq)']
 for n,(d,w) in ports.items():
  if n.startswith('master_gp0_axi_') or n.startswith('slave_hp0_axi_'):
   kind='gp' if n.startswith('master_') else 'hp';tail=n.split('_axi_')[1]
   if tail=='aclk':ps.append(f'.{n}({kind}0_aclk)');continue
   signal=kind+'_'+tail;lines.append('wire '+(f'[{w-1}:0] ' if w>1 else '')+signal+';');ps.append(f'.{n}({signal})');pl.append(f'.{signal}({signal})')
  elif n=='f2p_irq':ps.append('.f2p_irq(f2p_irq)')
  elif n=='p2f_rst0_n':ps.append('.p2f_rst0_n(arst_n)')
  elif n=='p2f_clk0':ps.append('.p2f_clk0(unused_p2f_clk0)')
  else:raise RuntimeError('unexpected PS port '+n)
 lines+=[module+' #(.P2F_CLK0_DIV(8),.Slave_AXI_HP0_DATA_WIDTH(64)) ps(\n'+',\n'.join(ps)+');',
         'motion_gp_ps_top #(.STEP_HIGH_CYCLES({4{64\'d3}}),.STEP_LOW_CYCLES({4{64\'d2}}),.DIR_SETUP_CYCLES({4{64\'d4}}),.DIR_HOLD_CYCLES({4{64\'d7}}),.EN_SETUP_CYCLES({4{64\'d5}}),.EN_DISABLE_CYCLES({4{64\'d3}}),.MAX_STEP_HZ({4{64\'d10000000}})) pl(\n'+',\n'.join(pl)+');','endmodule','']
 if a.report_only and (b/'top.v').read_text()!='\n'.join(lines):raise RuntimeError('built PS/top differs')
 (b/'top.v').write_text('\n'.join(lines));(b/'clock.sdc').write_text('create_clock -name board_100m -period 10 [get_ports clk_100m]\n')
 props_source=ROOT.parent/'bsp/work/gp_soc_prj/system/ip/system_ARM_Processor_System_0/system_ARM_Processor_System_0.tcl'
 props=props_source.read_text();old='ARM_Processor_System_f6ddd1d59490_Inst/DR1_PHY_PROCESSOR_SYSTEM_Inst'
 if props.count(old)!=4:raise RuntimeError('review PS property payload')
 (b/'ps-properties.tcl').write_text(props.replace(old,'ps/DR1_PHY_PROCESSOR_SYSTEM_Inst'))
 (b/'clock.adc').write_text('set_pin_assignment { clk_100m } { LOCATION = H16; IOSTANDARD = LVCMOS33; }\n')
 header=(ROOT.parent/'pl_interface/generated/interface_defs.vh').read_text();files=[];inputs={}
 for source in sorted((ROOT/'rtl').glob('*.v'))+sorted((ROOT.parent/'pl_motion/rtl').glob('*.v')):
  p=b/source.name;expanded=source.read_text().replace('`include "generated/interface_defs.vh"',header)
  if a.report_only and p.read_text()!=expanded:raise RuntimeError('built source differs '+str(source))
  p.write_text(expanded);files.append(p);inputs[str(source.relative_to(ROOT.parent))]=digest(source)
 script=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\n'
 for p in [Path(x['staged']) for x in ip['libraries'].values()]+files+[raw,b/'top.v']:script+=f'analyze -file {{{p.as_posix()}}}\n'
 script+='elaborate -top motion_soc_reference\noptimize_rtl\nread_adc clock.adc\nread_sdc ps-properties.tcl\nread_sdc clock.sdc\noptimize_gate -maparea gate.area\nupdate_timing\nreport_timing_summary -file gate.timing -path_num 3\nexport_db gate.db\nlegalize_phy_inst\nplace\nupdate_timing -mode manhattan\nreport_timing_summary -file place.timing -path_num 3\nroute\nupdate_timing -mode final\nreport_timing_summary -file route.timing -path_num 3\nreport_area -file route.area\ncheck_timing -verbose -file route.check\nreport_route_status -drc\nall_clocks -verbose\nexport_db route.db\nputs MOTION_SOC_REFERENCE_COMPLETE\nexit\n'
 (b/'run.tcl').write_text(script)
 if not a.report_only:
  with (b/'run.log').open('w') as log:r=subprocess.run([str(TD/'bin/td_commands_prompt.exe'),(b/'run.tcl').as_posix()],cwd=b,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
 log=(b/'run.log').read_text();result={'status':'REFERENCE_REMAINING_DIAGNOSTICS','not_deployable':True,'ps_sha256':digest(raw),'inputs':inputs,'shared_header':digest(ROOT.parent/'pl_interface/generated/interface_defs.vh'),'ip':ip,'reference_speed':2,'ps_properties_source':str(props_source),'ps_properties_source_sha256':digest(props_source),'clock_period_ns':10,'stages':{}}
 if (not a.report_only and r.returncode) or 'MOTION_SOC_REFERENCE_COMPLETE' not in log or 'ERROR:' in log:raise RuntimeError('PS reference failed: '+str(b/'run.log'))
 for stage in ['gate','place','route']:
  report=(b/(stage+'.timing')).read_text();w=float(re.search(r'SWNS:\s*([-\d.]+)ns',report)[1]);h=float(re.search(r'HWNS:\s*([-\d.]+)ns',report)[1]);result['stages'][stage]={'setup_wns_ns':w,'hold_wns_ns':h,'timing_pass':w>=0 and h>=0}
 result['critical_warnings']=[x for x in log.splitlines() if 'CRITICAL-WARNING' in x]
 area=(b/'route.area').read_text();check=(b/'route.check').read_text()
 result['route_resources']={key:int(re.search(r'^#'+key+r'\s+(\d+)',area,re.M)[1]) for key in ['lut6','reg','slice','eram','dsp','gclk','sclk']}
 result['check_timing_diagnostics']={key:int(re.search(pattern,check)[1]) for key,pattern in {'no_clock':r'checking no clock\((\d+)\)','dummy_nodes':r'checking dummy node\((\d+)\)','input_delay_missing':r'checking no input delay\((\d+)\)','output_delay_missing':r'checking no output delay\((\d+)\)'}.items()}
 result['actual_model_clock_names']=['board_100m','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_GP0S']
 result['build_directory']=str(b);result['validation_driver_parameters']='simulation-only 3/2/4/7/5/3 cycles, 10MHz; no physical motor outputs'
 # Synthesized-net estimates are reported separately; physical signoff is
 # final routed setup/hold, without hiding a failed earlier estimate.
 result['timing_pass']=result['stages']['route']['timing_pass'] and not result['critical_warnings']
 result['inputs_sha256_lf']={n:hashlib.sha256((ROOT.parent/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for n in inputs}
 (b/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 (ROOT/'MOTION_SOC_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['stages','critical_warnings']},indent=2))
 if not result['timing_pass']:raise RuntimeError('motion PS reference timing/critical diagnostics failed')
if __name__=='__main__':main()
