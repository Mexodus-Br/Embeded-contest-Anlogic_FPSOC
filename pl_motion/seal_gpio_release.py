"""Create the separate GPIO manifest after committing the tested source files."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'pl_motion/scope_test'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lf(b):return hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-commit',required=True);a=ap.parse_args()
 commit=subprocess.check_output(['git','rev-parse',a.source_commit+'^{commit}'],cwd=ROOT,text=True).strip()
 old=json.loads((ROOT/'pl_motion/MOTION_RELEASE.json').read_text(encoding='utf-8'))
 sources=set(old['source_sha256_lf'])
 sources.update(['HARDWARE.md','pl_dma/build_gpio_scope.py','pl_motion/.gitattributes',
  'pl_motion/generate_scope.py','pl_motion/archive_gpio_evidence.py','pl_motion/verify_gpio_delivery.py','pl_motion/seal_gpio_release.py',
  'pl_motion/tests/run_gpio_regressions.py','pl_motion/tests/run_scope_default.py','pl_motion/tests/run_scope_dma.py',
  'pl_motion/tests/scope_dma_scenarios.vh','pl_motion/tests/tb_scope_default.v',
  'pl_motion/scope_test/CONFIG.json','pl_motion/scope_test/analyze_edges.py','pl_motion/scope_test/audit_gpio_sta.py','pl_motion/scope_test/plot_waveforms.py'])
 sources.update(p.relative_to(ROOT).as_posix() for p in (OUT/'generated').iterdir() if p.is_file())
 source_hashes={n:lf((ROOT/n).read_bytes()) for n in sorted(sources)}
 for n,h in source_hashes.items():assert lf(subprocess.check_output(['git','show',commit+':'+n],cwd=ROOT))==h,n
 for n in ['SIM_RESULTS','DEFAULT_RESULTS','REGRESSION_RESULTS','EDGE_RESULTS']:
  assert json.loads((OUT/(n+'.json')).read_text())['status']=='PASS',n
 sta=json.loads((OUT/'STA_RESULTS.json').read_text());assert sta['timing_pass']
 evidence=[ROOT/'pl_motion/GPIO_HANDOFF.md',OUT/'PIN_REVIEW.json',OUT/'expected_edges.csv',OUT/'scope_waveforms.png',OUT/'scope_waveforms.svg']
 evidence+=list(OUT.glob('*_RESULTS.json'))+list((OUT/'evidence').rglob('*'))
 hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(evidence)) if p.is_file()}
 release={'source_commit':commit,'base_source_commit':old['source_commit'],
  'base_handoff_commit':'3a4ea5c8e56024bd2407916bafed48508e5a1e69','old_release_sha256':sha(ROOT/'pl_motion/MOTION_RELEASE.json'),
  'scope':'Confirmed J12 A0..A2 oscilloscope only; unchanged motion algorithms/ABI; no BSP edit/download/motor; mechanical mapping not frozen',
  'integration_entry':'pl_dma/rtl/motion_gp_ps_top.v','source_sha256_lf':source_hashes,'evidence_sha256':hashes,
  'vendor_ip_sha256':old['vendor_ip_sha256'],'schema_sha256':sha(ROOT/'pl_interface/schema.json'),
  'ps_sha256':sta['ps_sha256'],'ps_properties_source_sha256':sta['ps_properties_source_sha256'],
  'bitstream':{'path':str(Path(sta['build_directory'])/'scope-test.bit'),'sha256':sta['bitstream_sha256'],'paired_boot_image':False,'downloaded':False},
  'reference_package':'DR1M90GEG400','reference_speed':2,'physical_speed_confirmed':False,
  'clock_period_ns':10,'final_route':sta['stages']['route'],'output_datapath_bound_ns':20,
  'external_receiver':'asynchronous scope; no external100MHz synchronous setup signoff',
  'remaining_diagnostics':['vendor ERAM unused reset pins','mapped planner unused OFB','mapped plan_fifo DRC SLATR-1036/1038 notes'],
  'validation':{'default_zero':'PASS','affected_regressions':'PASS17','real_dma_coordinates_return_stop':'PASS',
   'physical_gpio_sta':'PASS reference2, remaining diagnostics reviewed','board_download':'NOT_EXECUTED',
   'oscilloscope_capture':'NOT_EXECUTED','driver_motor':'NOT_EXECUTED','bsp_boot_image_changes':'NOT_EXECUTED'},
  'failures_retained':['invalid ADC comment corrected','compile macro corrected','two manually interrupted incomplete simulations',
   'single-session Questa license contention','STOP test bit-mask truncation corrected','strict external100MHz output reference failed -1.342/-5.223ns']}
 (ROOT/'pl_motion/GPIO_RELEASE.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
 print('GPIO release manifest created for fixed source',commit,'sources',len(source_hashes),'evidence',len(hashes))
if __name__=='__main__':main()
