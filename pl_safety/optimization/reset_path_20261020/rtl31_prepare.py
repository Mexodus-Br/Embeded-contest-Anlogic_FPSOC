"""Clocked prepared FIFO RAM with exact forwarding; same public show-ahead cycle."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl31_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl30_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 s=(out/'motion_fifo.v').read_text();split=s.index('module motion_plan_fifo')
 original=s[:split];body=s[split:]
 body=replace(body,'localparam STORAGE_DEPTH=DEPTH+1;', 'localparam STORAGE_DEPTH=DEPTH;')
 body=replace(body,'reg [WIDTH-1:0] memory[0:STORAGE_DEPTH-1];',
  '(* ram_style="block" *) reg [WIDTH-1:0] memory[0:STORAGE_DEPTH-1];\n reg [WIDTH-1:0] ram_head,forward_data;reg forward_valid;')
 body=replace(body,'assign out_data=memory[read_pointer];', 'assign out_data=forward_valid ? forward_data:ram_head;')
 body=replace(body,'always @(posedge clk)if(store_push)memory[write_pointer]<=in_data;', '''// Prefetch the following head on a pop, otherwise refresh the current
 // head. A first enqueue or single-record pop/push bypasses the simultaneous
 // write explicitly, independent of ERAM cross-port collision mode.
 wire [PB-1:0] read_address=store_pop ?
  (read_pointer==STORAGE_DEPTH-1 ? {PB{1'b0}}:read_pointer+1'b1):read_pointer;
 always @(posedge clk)begin
  if(store_push)memory[write_pointer]<=in_data;
  ram_head<=memory[read_address];
  forward_valid<=rst_n && store_push && write_pointer==read_address;
  if(store_push && write_pointer==read_address)forward_data<=in_data;
 end''')
 body=replace(body,'if((wr>=rd ? wr-rd:wr+STORAGE_DEPTH-rd)!=count)$fatal(1,"physical prepared FIFO distance invariant");',
  'if((wr>=rd ? wr-rd:wr+STORAGE_DEPTH-rd)!=(count==DEPTH ? 0:count))$fatal(1,"physical prepared FIFO distance invariant");')
 body=replace(body,'if(store_pop && store_push && write_pointer==read_pointer)$fatal(1,"prepared RAM collision");','// Read/write collisions at read_address are explicitly forwarded above.')
 original=original.replace('// The spare address preserves old-head data for every valid full pop/push.',
  '// Clocked RAM prefetch plus explicit same-address forwarding preserves every valid record.')
 (out/'motion_fifo.v').write_bytes((original+body).encode())
 (out/'clocked_plan_notes.json').write_text(json.dumps({'hashes_computed':False,'external_cycles_added':0,
  'capacity':'logical/physical prepared slots remain8; all1197bits preserved',
  'method':'clocked RAM head read, next-head prefetch on pop, explicit full-width forwarding for first enqueue / one-record pop+push',
  'local_flush':'same-edge logical invalidation and registered private pointer cleanup retained from30',
  'mapping':'block-RAM eligibility only; no resource claim until actual synthesis and RAM audit',
  'pending_validation':True},indent=2)+'\n')
 print('Prepared isolated RTL31 clocked prepared FIFO, capacity8 unchanged')
if __name__=='__main__':main()
