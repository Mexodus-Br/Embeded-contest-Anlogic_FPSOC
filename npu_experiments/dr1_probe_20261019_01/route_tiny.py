"""Route the isolated Tiny fixture at the verified 100MHz clock contract."""
from pathlib import Path
import json,re
from run_resources import ROOT,THREADS,CLOCK_SDC,run_tcl

if __name__=='__main__':
    source=ROOT/'physical_tiny_100m/place.db'
    before=source.read_bytes()
    out=ROOT/'physical_tiny_route100';out.mkdir(exist_ok=True)
    (out/'fixture.sdc').write_text(CLOCK_SDC)
    text=f'''cd {{{out.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {{{source.as_posix()}}}
''' + THREADS + '''clear_user_sdc
read_sdc fixture.sdc
update_timing
report_timing_summary -file before_route.timing -path_num 1
route
update_timing -mode final
report_area -file route.area
report_timing_summary -file route.timing -path_num 5
report_route_status -file route.status
export_db route.db
puts "NPU_ROUTE_DONE"
exit
'''
    log=run_tcl(out,'route',text)
    assert 'NPU_ROUTE_DONE' in log
    assert before==source.read_bytes()
    timing=(out/'route.timing').read_text()
    active=re.findall(r'^\s*clk\d+:\s+([\d.]+)\s+\d+\s+(npu_\w+)',timing,re.M)
    assert sorted(active)==[('100.000','npu_config'),('100.000','npu_data')],active
    assert 'DeriveClock' not in timing
    (out/'status.json').write_text(json.dumps(dict(completed=True,threads=16,
        input_place_db_unchanged=True,active_clocks_mhz=100,
        isolated_virtual_boundary=True,model_qualified=False,integrated_system_verified=False),indent=2)+'\n')
    print('Isolated Tiny routing completed; no integrated or NPU execution claim.')
