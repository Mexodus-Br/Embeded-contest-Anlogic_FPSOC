"""Review final native pad/clock/exception/diagnostic reports independently."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def main():
 c=json.loads((OUT/'CONFIG.json').read_text(encoding='utf-8'))
 s=json.loads((OUT/'STA_RESULTS.json').read_text());b=Path(s['build_directory'])
 if not (b/'route.timing').exists():b=OUT/'evidence/final_gpio_sta'
 area=(b/'route.area').read_text();timing=(b/'route.timing').read_text()
 check=(b/'route.check').read_text();log=(b/'run.log').read_text()
 adc=(b/'clock.adc').read_text();sdc=(b/'clock.sdc').read_text()
 assert s['timing_pass'] and not s['critical_warnings']
 assert 'Device              : DR1M90GEG400' in timing and 'Speed               : 2' in timing
 assert 'Confidence          : Routed' in timing and 'Both (Slow and Fast)' in timing
 assert 'STNS: 0.000ns' in timing and 'HTNS: 0.000ns' in timing
 pads={}
 for p in c['pins']:
  m=re.search(r'^\s*'+p['port']+r'\s+OUTPUT\s+(\w+)\s+(\w+)\s+(\w+)\s+(\d+)\s+(\w+)\s+(\w+)\s+(\w+)',area,re.M)
  assert m and m.groups()==(p['ball'],'LVCMOS33','HRIO','8','NONE','OREG','NONE'),p
  assert re.search(p['port']+r'.*SLEWRATE = SLOW;.*PACKREG = ON;',adc),p
  pads[p['port']]={'j12_pin':p['pin'],'ball':m[1],'standard':m[2],'drive_ma':int(m[4]),'pull':m[5],'native_pack':m[6]}
 assert int(re.search(r'^#IO\s+(\d+)',area,re.M)[1])==10
 assert re.search(r'clk_100m\s+INPUT\s+H16\s+LVCMOS33',area)
 clocks={}
 for n in ['board_100m','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_GP0S']:
  assert re.search(r'100\.000\s+\d+\s+'+re.escape(n)+r'\s*$',timing,re.M),n
  clocks[n]=100
 assert not re.search(r'set_(?:false_path|multicycle_path)',sdc)
 assert 'create_clock -name board_100m -period 10' in sdc
 assert '-datapath_only 20' in sdc and '9            9            0            0   set_max_delay' in check
 for pattern in ['checking no clock(0)','checking clock definition(0)','checking invalid constraint(0)','checking combinational loops(0)','checking no path constraints(0)','checking no input delay(0)','checking no output delay(0)']:
  assert pattern in check,pattern
 assert check.count('DummyNode in Model:')==2
 assert 'DR1_PHY_ERAM' in check and '/planner/' in check and '.ofb' in check
 drc=log.split('start command "report_route_status -drc',1)[1].split('finish command "report_route_status',1)[0]
 assert all(x in drc for x in ['Run Pin Swap Checker','Run Net Connection Checker','Run Lut Bridge Checker','Run Multi Drive Checker','Run Clock Status Checker','Run Abnormal Path Checker'])
 assert not re.search(r'ERROR|CRITICAL-WARNING',drc)
 top=(b/'top.v').read_text()
 assert '.p2f_rst0_n(arst_n)' in top and '.arst_n(arst_n)' in top
 assert not re.search(r'output wire.*a3_',top)
 result={'status':'PASS_WITH_REVIEWED_REMAINING_DIAGNOSTICS','package':c['package'],'reference_speed':2,'physical_speed_confirmed':False,
 'pads':pads,'native_pad_count':10,'clock_mhz':clocks,'coverage_percent':float(re.search(r'STA coverage\s*:\s*([\d.]+)%',timing)[1]),
 'route_setup_wns_ns':s['stages']['route']['setup_wns_ns'],'route_hold_wns_ns':s['stages']['route']['hold_wns_ns'],
 'output_constraint':'nine asynchronous scope outputs only: datapath-only max20ns; internal clock10ns; no clocked external receiver signoff',
 'exceptions_total_dominated_shadowed_ignored':[9,9,0,0],'remaining_dummy_categories':['vendor ERAM unused reset pins','motion planner unused mapped slice OFB'],
 'native_drc_notes':'SLATR-1036/1038 on two mapped plan_fifo RAM slices retained in run.log; final route checker completed without error/critical warning',
 'reset_review':'PS p2f_rst0_n to unchanged synchronized control reset; default/active RTL reset states checked by scope benches; physical configuration window unmeasured',
 'reports_sha256':{n:hashlib.sha256((b/n).read_bytes()).hexdigest() for n in ['route.area','route.timing','route.check','run.log','clock.adc','clock.sdc','top.v']}}
 (OUT/'IO_AUDIT_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS final nine pads/OREG/3.3V/reference2, internal100MHz, bounded async output paths and reviewed remaining diagnostics')
if __name__=='__main__':main()
