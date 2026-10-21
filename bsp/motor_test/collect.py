"""Collect raw evidence without hashing logs/intermediate artifacts."""
from pathlib import Path
import shutil,json,csv
R=Path(__file__).resolve().parents[2];W=R/'bsp/work/motor3125_soc_prj';D=R/'bsp/motor_test'
E=R/'bsp/evidence/motor3125-20261021';E.mkdir(exist_ok=True)
for n in ['build.log','build.tcl','gate.timing','place.timing','route.timing','route.area','route.check','route.drc','bitgen.log','hpf-final.log','review.json']:
    if (W/n).exists():shutil.copyfile(W/n,E/n)
for p in W.glob('attempt_*.log'):shutil.copyfile(p,E/p.name)
for p in W.glob('td_*.log*'):shutil.copyfile(p,E/p.name)
for src,name in [(W/'system/hdl/system_wrapper.v','system_wrapper.v'),(W/'gp/gp.adc','gpio.adc'),(W/'gp/gp.sdc','gpio.sdc'),(W/'gp/ps-generated-properties.tcl','ps-properties.tcl')]:shutil.copyfile(src,E/name)
log=(W/'build.log').read_text(errors='replace')
marker='RUN-1002 : start command "report_route_status -drc -file route.drc"'
if marker in log:
    tail=log[log.index(marker):]
    end=tail.find('RUN-1003 : finish command "report_route_status')
    if end>=0:(E/'route-drc-excerpt.log').write_text(tail[:end])
for n in ['simulation','real_dma','real_dma_attempt2']:
    dest=E/n;dest.mkdir(exist_ok=True)
    for p in (W/n).iterdir():
        if p.is_file() and p.suffix in ['.log','.csv','.vcd']:
            shutil.copyfile(p,dest/p.name)
rows=list(csv.DictReader((W/'real_dma_attempt2/observed_edges.csv').open()))
summary=[]
for phase in [1,2,3]:
    for axis in range(3):
        selected=[x for x in rows if int(x['phase'])==phase and int(x['axis'])==axis and x['signal']=='step']
        rises=[int(x['cycle']) for x in selected if x['value']=='1']
        falls=[int(x['cycle']) for x in selected if x['value']=='0']
        assert len(rises)==len(falls)
        highs=[f-r for r,f in zip(rises,falls)];lows=[r-f for f,r in zip(falls,rises[1:])]
        assert set(highs)=={3125}
        assert not lows or min(lows)>=3125
        summary.append({'phase':phase,'axis':axis,'steps':len(rises),'high_cycles':3125,'minimum_low_cycles':min(lows) if lows else None})
(E/'waveform-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (E/'predicted-500ms-edges.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['phase','axis','slot','direction','rise_cycle_from_point_start','fall_cycle_from_point_start','high_us','prediction_only'])
    for phase in [1,2]:
        for axis in range(3):
            for slot in range(124):
                emit=axis==1 or (axis==0 and slot==0) or (axis==2 and slot!=1)
                if emit:
                    rise=3127+slot*(50000000-3127)//124
                    positive=(axis!=2) if phase==1 else (axis==2)
                    writer.writerow([phase,axis,slot,int(positive),rise,rise+3125,31.25,True])
print(E)
