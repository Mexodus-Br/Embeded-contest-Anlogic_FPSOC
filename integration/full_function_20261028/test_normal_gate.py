"""Actual isolated service gates; injected READY is a test condition, not HOME evidence."""
from pathlib import Path
import argparse,subprocess,sys
H=Path(__file__).resolve().parent;R=H.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--hardware-directory',default='hardware');args=parser.parse_args();assert args.hardware_directory.replace('_','').isalnum();G=H/args.hardware_directory/'gp'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
out=H/'artifacts'/('normal-gate' if args.hardware_directory=='hardware' else 'normal-gate-'+args.hardware_directory);out.mkdir(exist_ok=False);sim=Simulator(out)
base=subprocess.check_output(['git','show','05686d4:pl_safety/tests/tb_safety.v'],cwd=R).decode()
base=base.replace('(MODE==8 || MODE==31) ? 0:1','0')
text=base[:base.index('initial begin\n')]+'''initial begin
 repeat(4)@(negedge clk);rst_n=1;repeat(20)@(negedge clk);
 check(!dut.motion.normal_ok,"ordinary motion requires HOME");
 mcommand(`PLI_CMD_ENABLE,7);check(!dut.motion.ack_accepted,"ENABLE before HOME refused");
 force dut.controller.state=`SAF_STATES_READY;
 force dut.position_valid=4'b0111;
 repeat(10)@(negedge clk);
 check(dut.motion.normal_ok,"explicit full-function profile can admit normal motion in READY");
 mcommand(`PLI_CMD_ENABLE,7);check(dut.motion.ack_accepted,"ENABLE with valid HOME counts accepted");
 mcommand(`PLI_CMD_REBASE,7);check(!dut.motion.ack_accepted,"public REBASE still prohibited");
 force dut.controller.state=`SAF_STATES_NEED;
 repeat(10)@(negedge clk);
 check(!dut.motion.normal_ok,"loss of HOME inhibits normal motion again");
 $display("PASS full-function normal gate checks=%0d",checks);$finish;
end
endmodule
'''
p=out/'test.v';p.write_text(text);exe=out/'test.vvp'
names=['safety_controller','safety_inputs','safety_regs','safety_motion_service','safety_interlock','safety_interlock_regs','motion_service','continuous_motion','motion_executor','motion_planner','motion_fifo','motion_stream_rx']
(out/'compile.log').write_text(sim.compile([G/(n+'.v') for n in names]+[p],'tb_safety',exe,includes=[G,R/'pl_interface']))
log=sim.simulate(exe,timeout=90);(out/'run.log').write_text(log);assert 'PASS' in log;print(log)
