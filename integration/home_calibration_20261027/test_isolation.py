"""Verify production READY still rejects normal motion; isolated interlock regression."""
from pathlib import Path
import subprocess,sys
H=Path(__file__).resolve().parent;R=H.parents[1];G=H/'hardware/gp'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
O=H/'artifacts/isolation-corrected';O.mkdir(exist_ok=False);sim=Simulator(O)
def run(name,text,sources,top):
 p=O/(name+'.v');p.write_text(text);v=O/(name+'.vvp')
 log=sim.compile(sources+[p],top,v,includes=[G,R/'pl_interface']);(O/(name+'-compile.log')).write_text(log)
 log=sim.simulate(v,timeout=90);(O/(name+'.log')).write_text(log);assert 'PASS' in log;print(log)
t=subprocess.check_output(['git','show','05686d4:pl_safety/tests/tb_safety.v'],cwd=R).decode()
t=t.replace('(MODE==8 || MODE==31) ? 0:1','0')
t=t[:t.index('initial begin\n')]+"""initial begin
 repeat(4)@(negedge clk);rst_n=1;repeat(20)@(negedge clk);
 // Inject controller READY solely to exercise the post-HOME normal-command gate.
 force dut.controller.state=`SAF_STATES_READY;
 force dut.controller.position_valid=4'b0111;
 repeat(10)@(negedge clk);
 check(!dut.motion.normal_ok,"calibration-only remains inhibited in READY");
 mcommand(`PLI_CMD_ENABLE,7);check(!dut.motion.ack_accepted,"ENABLE refused");
 mcommand(`PLI_CMD_OPEN_SESSION,0);check(!dut.motion.ack_accepted,"OPEN_SESSION refused");
 mcommand(`PLI_CMD_START,0);check(!dut.motion.ack_accepted,"START refused");
 check(!running && !session && step==0,"no ordinary motion output");
 $display("PASS calibration-only READY gate checks=%0d",checks);$finish;
end
endmodule
"""
names=['safety_controller','safety_inputs','safety_regs','safety_motion_service','safety_interlock','safety_interlock_regs','motion_service','continuous_motion','motion_executor','motion_planner','motion_fifo','motion_stream_rx']
run('gate',t,[G/(n+'.v') for n in names],'tb_safety')
t=(R/'pl_safety/tests/tb_interlock.v').read_text().replace("32'd0,32'd0,6'd0,1'b0,1'b0,1'b0);","32'd0,32'd0,6'd0,1'b0,1'b0,1'b0,2'd0,,1'b1);")
run('interlock',t,[G/'safety_interlock.v',G/'rs485_light_parse.v'],'tb_interlock')
