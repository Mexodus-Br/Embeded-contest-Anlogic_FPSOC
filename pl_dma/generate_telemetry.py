"""Opt-in independent controller and six-way fabric; old generators unchanged."""
import argparse,json,re,sys
from pathlib import Path
from prepare_ip import ROOT
import generate_top
sys.path.insert(0,str(ROOT.parent/'pl_motion'))
from generate_motion import PARAM,PN,BIND,OUTPUT_BIND
SIG=['awaddr','araddr','wdata','wstrb','awvalid','awready','wvalid','wready','bvalid','bready','bresp','arvalid','arready','rvalid','rready','rdata','rresp']
W={'awaddr':33,'araddr':33,'wdata':32,'wstrb':4,'bresp':2,'rdata':32,'rresp':2}
def portnames(header):
 out={}
 for d,w,names in re.findall(r'\b(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',header,re.S):
  for n in names.strip().rstrip(',').split(','):out[n.strip()]=(d,int(w)+1 if w else 1)
 return out
def render():
 result={};p=json.loads((ROOT.parent/'pl_interface/schema.json').read_text(encoding='utf-8'))['rs485_telemetry']
 dma=generate_top.render().replace('module dma_loopback_top(','module telemetry_dma_lite_top(').replace('`PLI_DMA_DMA_LOOPBACK_V1_','`PLI_TELEM_DMA_').replace('dma_lite_guard guard','telemetry_dma_guard guard')
 dma=dma.replace('output wire [31:0] loop_occupancy','input wire [63:0] stream_data,input wire [7:0] stream_keep,input wire stream_last,stream_valid,output wire stream_ready,stream_rst_n,hp_idle')
 a=dma.index('wire fifo_arst_n=');b=dma.index('wire [2:0] bridge_awsize',a)
 dma=dma[:a]+'''wire stream_arst_n=control_rst_n && d_s2mm_prmry_reset_out_n;
reg [1:0] stream_release;always @(posedge clk_100m or negedge stream_arst_n) if(!stream_arst_n) stream_release<=0;else stream_release<={stream_release[0],1'b1};
assign stream_rst_n=stream_release[1];
assign d_s_axis_s2mm_tdata=stream_data;assign d_s_axis_s2mm_tkeep=stream_keep;assign d_s_axis_s2mm_tlast=stream_last;
assign d_s_axis_s2mm_tvalid=stream_valid;assign stream_ready=d_s_axis_s2mm_tready;
assign d_s_axis_s2mm_tuser=0;assign d_s_axis_s2mm_tid=0;assign d_s_axis_s2mm_tdest=0;assign d_m_axis_mm2s_tready=1'b0;
assign f2p_irq=(!arst_n || !control_rst_n) ? 16'd0 : (d_s2mm_introut ? (16'd1<<`PLI_TELEM_DMA_IRQ_LINE) : 16'd0);
reg [7:0] outstanding_writes;
always @(posedge clk_100m or negedge arst_n) if(!arst_n) outstanding_writes<=0;
else case({hp_awvalid && hp_awready,hp_bvalid && hp_bready}) 2'b10:outstanding_writes<=outstanding_writes+1'b1;2'b01:outstanding_writes<=outstanding_writes-1'b1;endcase
assign hp_idle=outstanding_writes==0 && !hp_awvalid && !hp_wvalid && !hp_bvalid;
''' +dma[b:]
 result['telemetry_dma_lite_top.v']=dma
 guard=(ROOT/'rtl/dma_lite_guard.v').read_text().replace('module dma_lite_guard(','module telemetry_dma_guard(').replace('`PLI_DMA_DMA_LOOPBACK_V1_','`PLI_TELEM_DMA_')
 a=guard.index(' wire length_bad=');b=guard.index(' assign s_awready',a)
 allowed=' || '.join(f'a[9:0]==10\'h{x:03x}' for x in p['dma']['read_offsets'])
 guard=guard.replace('  else address_error=0;',f'  else if(!({allowed})) address_error=2;\n  else address_error=0;')
 guard=guard[:guard.index(' wire length_bad=')]+''' wire length_bad=wa[9:0]==10'h058 && (wd==0 || wd>65535);
 wire address_bad=(wa[9:0]==10'h048 && wd[2:0]!=0) || (wa[9:0]==10'h04c && wd!=0);
 wire [1:0] we=address_error(wa)!=0 ? address_error(wa) : (st!=15 || length_bad || address_bad) ? 2 : 0;
 wire [1:0] re=address_error(ra);
'''+guard[guard.index(' assign s_awready'):]
 result['telemetry_dma_guard.v']=guard
 # Generic router: endpoint1 is existing DMA full guard for all unmapped windows.
 router=(ROOT/'rtl/axi_lite_three_way.v').read_text().replace('axi_lite_three_way','axi_lite_six_way')
 for a,b in [('98:0','197:0'),('95:0','191:0'),('11:0] m_wstrb','23:0] m_wstrb'),('2:0] m_awvalid','5:0] m_awvalid'),('2:0] m_awready','5:0] m_awready'),('5:0] m_bresp','11:0] m_bresp'),('reg [1:0] write_sel,read_sel','reg [2:0] write_sel,read_sel'),("3'b001","6'b000001"),('{wa,wa,wa}','{6{wa}}'),('{ra,ra,ra}','{6{ra}}'),('{wd,wd,wd}','{6{wd}}'),('{st,st,st}','{6{st}}')]:router=router.replace(a,b)
 for port in ['awaddr','araddr']:
  old=f'{port if False else "s_"+port}[32:12]==MOTION_BASE[32:12] ? 2 : 1'
  new=f's_{port}[32:12]==MOTION_BASE[32:12] ? 2 : s_{port}[32:12]==RS_BASE[32:12] ? 3 : s_{port}[32:12]==CACHE_BASE[32:12] ? 4 : s_{port}[32:12]==TELEM_DMA_BASE[32:12] ? 5 : 1'
  router=router.replace(old,new)
 router=router.replace(' reg ah,'," localparam [32:0] RS_BASE={1'b0,`PLI_RS485_GP_RS485_V1_BASE},CACHE_BASE={1'b0,`PLI_TELEM_BASE},TELEM_DMA_BASE={1'b0,`PLI_TELEM_DMA_BASE};\n reg ah,")
 result['axi_lite_six_way.v']=router
 old=(ROOT/'rtl/motion_shared_lite_top.v').read_text();head=old.split(')(\n',1)[1].split(');',1)[0];hphead='\n'.join(line.replace('hp_','hp1_') for line in head.splitlines() if re.search(r'\bhp_',line)).rstrip().rstrip(',')
 extras='input wire rs485_rx,output wire rs485_tx,rs485_de,output wire hp1_aclk,\n'+hphead
 text=old.replace('module motion_shared_lite_top','module rs485_shared_lite_top')
 pos=text.index(');',text.index('module '));text=text[:pos].rstrip()+',\n'+extras+'\n'+text[pos:]
 text=text.replace('axi_lite_three_way router','axi_lite_six_way router')
 for n in SIG:text=text.replace(f'wire [{3*W.get(n,1)-1}:0] m_{n};',f'wire [{6*W.get(n,1)-1}:0] m_{n};')
 # Existing time source is read-only exported from original probe instance.
 text=text.replace('wire gp_irq,motion_irq;','wire gp_irq,motion_irq,rs_irq,telem_irq;wire [15:0] independent_dma_irq;wire [63:0] system_time_us;')
 probe=(ROOT.parent/'pl_motion/rtl/gp_control_regs.v').read_text().replace('module gp_control_regs(','module rs485_probe_time_regs(').replace('    output wire irq','    output wire [63:0] shared_time_us,\n    output wire irq').replace('    reg [63:0] timestamp;','    reg [63:0] timestamp;\n    assign shared_time_us=timestamp;')
 result['rs485_probe_time_regs.v']=probe
 text=text.replace('gp_control_regs registers(', 'rs485_probe_time_regs registers(.shared_time_us(system_time_us),')
 # timestamp_us is already an output in the existing probe.
 def bind(i):return ','.join(f'.s_{n}(m_{n}[{i*W.get(n,1)}+: {W.get(n,1)}])' for n in SIG)
 extra='''wire completed_valid;wire [255:0] completed_raw;wire [31:0] generation,revision;wire [159:0] periods;wire [4:0] query_mask;
wire [63:0] telemetry_data;wire [7:0] telemetry_keep;wire telemetry_last,telemetry_valid,telemetry_ready,telemetry_rst_n,hp1_idle;
'''
 extra+='rs485_gp_bridge rs485(.clk(clk_100m),.rst_n(rst_n),.time_us(system_time_us),.rx(rs485_rx),.tx(rs485_tx),.de(rs485_de),.irq(rs_irq),'+bind(3)+',.completed_valid(completed_valid),.completed_raw(completed_raw),.completed_generation(generation),.completed_revision(revision),.current_periods(periods),.current_mask(query_mask));\n'
 extra+='rs485_telem_top telemetry(.clk(clk_100m),.rst_n(rst_n),.dma_ready(telemetry_rst_n),.dma_quiescent(hp1_idle),.time_us(system_time_us),.event_valid(completed_valid),.event_raw(completed_raw),.collector_generation(generation),.event_revision(revision),.active_period_us(periods),.active_mask(query_mask),.irq(telem_irq),'+bind(4)+',.m_data(telemetry_data),.m_keep(telemetry_keep),.m_last(telemetry_last),.m_valid(telemetry_valid),.m_ready(telemetry_ready));\n'
 hpnames=portnames(hphead)
 extra+='telemetry_dma_lite_top telemetry_dma(.clk_100m(clk_100m),.arst_n(arst_n),.control_rst_n(),.hp0_aclk(hp1_aclk),.f2p_irq(independent_dma_irq),'+bind(5)+','+','.join('.'+n.replace('hp1_','hp_')+'('+n+')' for n in hpnames)+',.stream_data(telemetry_data),.stream_keep(telemetry_keep),.stream_last(telemetry_last),.stream_valid(telemetry_valid),.stream_ready(telemetry_ready),.stream_rst_n(telemetry_rst_n),.hp_idle(hp1_idle));\n'
 text=text.replace('assign f2p_irq=',extra+'assign f2p_irq=independent_dma_irq | (rs_irq ? (16\'d1<<`PLI_RS485_GP_RS485_V1_IRQ_LINE):16\'d0) | (telem_irq ? (16\'d1<<`PLI_TELEM_IRQ_LINE):16\'d0) | ')
 result['rs485_shared_lite_top.v']=text
 extra_names=['rs485_rx','rs485_tx','rs485_de','hp1_aclk']+list(hpnames)
 for oldname,newname,childold,childnew in [('motion_gp_full_top','rs485_gp_full_top','motion_shared_lite_top','rs485_shared_lite_top'),('motion_gp_ps_top','rs485_gp_ps_top','motion_gp_full_top','rs485_gp_full_top')]:
  text=(ROOT/'rtl'/f'{oldname}.v').read_text().replace('module '+oldname,'module '+newname).replace(childold+' ',childnew+' ')
  pos=text.index(');',text.index('module '));text=text[:pos].rstrip()+',\n'+extras+'\n'+text[pos:]
  pos=text.index(childnew+' ');opening=text.index('(',pos+len(childnew+' '+BIND))
  text=text[:opening+1]+','.join('.'+n+'('+n+')' for n in extra_names)+',\n'+text[opening+1:]
  result[newname+'.v']=text
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args()
 for n,t in render().items():
  p=ROOT/'rtl'/n
  if a.check:
   if p.read_text()!=t:raise RuntimeError('stale '+n)
  else:p.write_bytes(t.encode())
