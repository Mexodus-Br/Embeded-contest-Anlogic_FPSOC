"""Prepare isolated same-edge source predecode plus full-word epoch lookahead.

No production mutation. Byte comparisons protect the candidate13 starting point.
"""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=HERE/'sources_r2'
def change(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
def main():
 OUT.mkdir(exist_ok=False)
 old=ROOT/'pl_safety/optimization/interlock_candidate14'
 spec=importlib.util.spec_from_file_location('proto14',old/'integrated_probe.py')
 p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
 p.OVERLAY=old/'integrated_sources_r2'
 assert not p.OVERLAY.exists()
 p.prepare()
 scope=json.loads((p.OVERLAY/'scope.json').read_text())['logical_source_paths']
 files={k:(p.OVERLAY/k).read_text() for k in scope}
 files['pl_rs485/rtl/rs485_transaction.v']=(ROOT/'pl_rs485/rtl/rs485_transaction.v').read_text()
 for logical in files:
  if logical.endswith('.v'):
   assert (ROOT/logical).read_bytes()==(ROOT/'pl_safety/build/interlock_route13/gp'/Path(logical).name).read_bytes(),logical
 t=files['pl_rs485/rtl/rs485_transaction.v']
 t=change(t,',parameter integer NORMAL_CYCLES=',',parameter INTERLOCK_PREDECODE=0,parameter [79:0] PROTECTION_ADDRS=0\n ,parameter integer NORMAL_CYCLES=')
 t=change(t,'output reg [31:0] accepted,errors,ignored_rx);','output reg [31:0] accepted,errors,ignored_rx,output reg [5:0] protection_decoded);')
 t=change(t,' wire tx_busy,tx_done,rv,rf,line_idle;', ''' // Capture the fixed-format decode on the SAME EMIT edge as push_data.
 // No FIFO/PS/DMA dependency and no additional detection pipeline stage.
 wire protection_known=command==query_code(3'd4) && status==`RS_STATUS_VALID &&
  length==query_length(3'd4) && payload[47:8]==0 && (payload[7:0]==1 || payload[7:0]==2);
 wire [2:0] protection_axes={address==PROTECTION_ADDRS[16+:8],
  address==PROTECTION_ADDRS[8+:8],address==PROTECTION_ADDRS[0+:8]} & {3{protection_known}};
 wire tx_busy,tx_done,rv,rf,line_idle;''')
 t=change(t,'push<=0;push_data<=0;','push<=0;push_data<=0;protection_decoded<=0;')
 t=change(t,'    EMIT: begin\n', '''    EMIT: begin
     protection_decoded<=INTERLOCK_PREDECODE ?
       {protection_axes & {3{payload[7:0]==1}},protection_axes}:6'd0;
''')
 files['pl_rs485/rtl/rs485_transaction.v']=t
 m=files['pl_rs485/rtl/rs485_multirate.v']
 m=change(m,'module rs485_multirate #(\n','module rs485_multirate #(\n parameter INTERLOCK_PREDECODE=0,\n')
 m=change(m,'output wire [31:0] next_revision);','output wire [31:0] next_revision,output wire [5:0] observe_protection);')
 m=change(m,'rs485_transaction #(.CLK_HZ(CLK_HZ)', 'rs485_transaction #(.INTERLOCK_PREDECODE(INTERLOCK_PREDECODE),.PROTECTION_ADDRS(SLAVE_ADDRS),.CLK_HZ(CLK_HZ)')
 m=change(m,'.push(push),.push_data(push_data),.accepted(accepted)', '.push(push),.push_data(push_data),.protection_decoded(observe_protection),.accepted(accepted)')
 files['pl_rs485/rtl/rs485_multirate.v']=m
 b=files['pl_rs485/rtl/rs485_gp_bridge.v']
 b=change(b,'output wire [31:0] next_generation,next_revision);','output wire [31:0] next_generation,next_revision,output wire [5:0] completed_protection);')
 b=change(b,'rs485_multirate #(.CLK_HZ(CLK_HZ)', 'rs485_multirate #(.INTERLOCK_PREDECODE(INTERLOCK_SUPPORT),.CLK_HZ(CLK_HZ)')
 # First observe_data connection belongs to collector; GP cache stays unchanged.
 assert b.count('.observe_push(push),.observe_data(push_data),')==2
 b=b.replace('.observe_push(push),.observe_data(push_data),','.observe_push(push),.observe_data(push_data),.observe_protection(completed_protection),',1)
 files['pl_rs485/rtl/rs485_gp_bridge.v']=b
 c=files['pl_safety/rtl/safety_interlock.v']
 c=change(c,'parameter LOOKAHEAD_EPOCH=0','parameter LOOKAHEAD_EPOCH=0,parameter FEEDBACK_PREDECODE=0')
 c=change(c,'input wire [31:0] next_generation,next_revision\n','input wire [31:0] next_generation,next_revision,\n input wire [5:0] feedback_predecoded\n')
 c=change(c,'wire feedback_valid=feedback_commit && protection_record &&','wire feedback_valid=feedback_commit && (FEEDBACK_PREDECODE ? |feedback_predecoded[2:0]:protection_record) &&')
 c=change(c,'wire [2:0] update_axis=feedback_axis & active_axes','wire [2:0] update_axis=(FEEDBACK_PREDECODE ? feedback_predecoded[2:0]:feedback_axis) & active_axes')
 c=change(c,'wire [2:0] protected_axis=feedback_axis & {3{feedback_valid && enum_raw==1}};', 'wire [2:0] protected_axis=(FEEDBACK_PREDECODE ? feedback_predecoded[5:3]:\n   (feedback_axis & {3{enum_raw==1}})) & {3{feedback_valid}};')
 files['pl_safety/rtl/safety_interlock.v']=c
 s=files['pl_safety/rtl/safety_motion_service.v']
 s=change(s,'input wire feedback_commit,input wire [255:0] feedback_raw,','input wire feedback_commit,input wire [255:0] feedback_raw,input wire [5:0] feedback_predecoded,')
 s=change(s,'#(.LOOKAHEAD_EPOCH(1)) monitor(', '#(.LOOKAHEAD_EPOCH(1),.FEEDBACK_PREDECODE(1)) monitor(.feedback_predecoded(feedback_predecoded),')
 files['pl_safety/rtl/safety_motion_service.v']=s
 g=files['pl_safety/generate_top.py']
 g=change(g,'input wire feedback_commit,input wire [255:0] feedback_raw,','input wire feedback_commit,input wire [255:0] feedback_raw,input wire [5:0] feedback_predecoded,')
 g=change(g,"'.feedback_commit(feedback_commit),.feedback_raw(feedback_raw),'+", "'.feedback_commit(feedback_commit),.feedback_raw(feedback_raw),.feedback_predecoded(feedback_predecoded),'+")
 g=change(g,'wire [31:0] collector_next_generation,collector_next_revision;', 'wire [5:0] completed_protection;\\nwire [31:0] collector_next_generation,collector_next_revision;')
 g=change(g,"'.feedback_commit(completed_valid),.feedback_raw(completed_raw),'+", "'.feedback_commit(completed_valid),.feedback_raw(completed_raw),.feedback_predecoded(completed_protection),'+")
 g=change(g,"'.interlock_idle(interlock_idle),.interlock_idle_off(interlock_idle_off),'+\n     '.interlock_run", "'.completed_protection(completed_protection),.interlock_idle(interlock_idle),.interlock_idle_off(interlock_idle_off),'+\n     '.interlock_run")
 files['pl_safety/generate_top.py']=g
 ns={'__name__':'candidate15','__file__':str(ROOT/'pl_safety/generate_top.py')}
 exec(compile(g,ns['__file__'],'exec'),ns)
 for name,data in ns['render']().items():
  if data.encode()!=(ROOT/'pl_safety/generated'/name).read_bytes():
   assert name in ['interlock_motion_dma_lite_top.v','interlock_rs485_shared_lite_top.v']
   files['pl_safety/generated/'+name]=data
 for logical,data in files.items():
  f=OUT/logical;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data.encode())
 (OUT/'scope.json').write_text(json.dumps({'production_modified':False,'hashes_computed':False,'paths':list(files)},indent=2)+'\n')
 print('PASS isolated candidate15 preparation',len(files))
if __name__=='__main__':main()
