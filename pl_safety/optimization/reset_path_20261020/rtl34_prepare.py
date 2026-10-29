"""Keep public queue handshakes; cofactor executor VALID behind its stop gate."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl34_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl33_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 s=(out/'continuous_motion.v').read_text()
 s=replace(s,'.plan_valid(launch),.plan_ready(executor_ready),.plan_available(executor_available),',
  '.plan_valid(prepared_executor_valid),.plan_ready(executor_ready),.plan_available(executor_available),')
 s=replace(s,'wire maintenance_ok=!session_valid', '''// Executor plan_ready already incorporates the original direct stop,
 // fault and disable gates. With session ownership, any other cancellation
 // also asserts its stop_req. An unaccepted VALID may therefore use the
 // cancellation-free storage request. Its accepted handshake is identical;
 // public prepared_pop/events remain unchanged. Exclude normal END cleanup.
 wire prepared_executor_valid=prepared_storage_ready && !(at_boundary && active_end);
 wire maintenance_ok=!session_valid''')
 extra='''
// synthesis translate_off
always @(posedge clk)if(rst_n && executor_ready)
 if(prepared_executor_valid !== launch)$fatal(1,"executor accepted VALID cofactor mismatch");
// synthesis translate_on
'''
 (out/'continuous_motion.v').write_bytes(s.replace('endmodule',extra+'endmodule').encode())
 (out/'executor_valid_notes.json').write_text(json.dumps({'hashes_computed':False,'new_registers':0,'external_cycles_added':0,
  'proof':'executor_ready implies original direct safety gate clear; session-valid && cancel asserts executor stop; END cleanup excluded; hence accepted VALID equals original launch',
  'unchanged':'public prepared_pop/level/events, executor direct safety/STEP/DIR/EN/position implementation',
  'status':'isolated module validation pending'},indent=2)+'\n')
 print('Prepared isolated RTL34 executor VALID cofactor; product remains29')
if __name__=='__main__':main()
