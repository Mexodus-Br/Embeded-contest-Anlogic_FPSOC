"""Compare complete pin/count traces against frozen RTL over all 32 scenarios."""
from pathlib import Path
import subprocess,sys
H=Path(__file__).resolve().parent;R=H.parents[1];G=H/'hardware/gp'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
out=H/'artifacts/executor-equivalence';out.mkdir(exist_ok=False);sim=Simulator(out)
t=subprocess.check_output(['git','show','05686d4:pl_safety/tests/tb_safety.v'],cwd=R).decode()
t=t.replace('(MODE==8 || MODE==31) ? 0:1','(MODE==8 || MODE==31) ? 99:1')
t=t.replace('endmodule','always @(negedge clk)if(rst_n)$display("TRACE %h %h %h %h %h %h %h %h %h %h",step,dir,en,valid,position,pulses,busy,session,running,stopped);\nendmodule')
bench=out/'bench.v';bench.write_text(t)
names=['safety_controller.v','safety_inputs.v','safety_regs.v','safety_motion_service.v','safety_interlock.v','safety_interlock_regs.v','motion_service.v','continuous_motion.v','motion_executor.v','motion_planner.v','motion_fifo.v','motion_stream_rx.v']
cycles=0
for mode in range(32):
    traces=[]
    for label,executor in [('frozen',G/'motion_executor.v'),('candidate',H/'rtl/motion_executor.v')]:
        target=out/(label+'-'+str(mode)+'.vvp')
        sources=[executor if n=='motion_executor.v' else G/n for n in names]+[bench]
        compile_log=sim.compile(sources,'tb_safety',target,includes=[G,R/'pl_interface'],extra=['-Ptb_safety.MODE='+str(mode)])
        (out/(label+'-'+str(mode)+'-compile.log')).write_text(compile_log)
        log=sim.simulate(target,timeout=90);(out/(label+'-'+str(mode)+'.log')).write_text(log)
        assert 'PASS' in log,log
        traces.append([line for line in log.splitlines() if line.startswith('TRACE ')])
    assert traces[0]==traces[1],('pin/count divergence',mode)
    cycles+=len(traces[0])
print('PASS exact STEP/DIR/EN/position/valid/pulse/session/state traces:',cycles,'cycles, 32 safety scenarios; no hashes')
