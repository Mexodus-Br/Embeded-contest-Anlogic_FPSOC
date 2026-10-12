"""Generate motion wiring using the validated DMA/PS front ends; keep loopback."""
import argparse,re,sys
from pathlib import Path
from prepare_ip import ROOT
sys.path.insert(0,str(ROOT.parent/'pl_motion'))
PARAM='''#(
 parameter FIFO_DEPTH=`PLI_MOTION_GP_MOTION_V1_RAW_DEPTH,PLAN_DEPTH=`PLI_MOTION_GP_MOTION_V1_PLAN_DEPTH,
 parameter START_MIN_POINTS=`PLI_MOTION_GP_MOTION_V1_START_MIN_POINTS,
 parameter [255:0] STEP_HIGH_CYCLES=0,STEP_LOW_CYCLES=0,DIR_SETUP_CYCLES=0,DIR_HOLD_CYCLES=0,
 parameter [255:0] EN_SETUP_CYCLES=0,EN_DISABLE_CYCLES=0,MAX_STEP_HZ=0,
 parameter [3:0] EN_ACTIVE_LEVEL=15
)'''
PN=['FIFO_DEPTH','PLAN_DEPTH','START_MIN_POINTS','STEP_HIGH_CYCLES','STEP_LOW_CYCLES','DIR_SETUP_CYCLES','DIR_HOLD_CYCLES','EN_SETUP_CYCLES','EN_DISABLE_CYCLES','MAX_STEP_HZ','EN_ACTIVE_LEVEL']
BIND='#('+','.join('.'+n+'('+n+')' for n in PN)+')'
SIG=['awaddr','araddr','wdata','wstrb','awvalid','awready','wvalid','wready','bvalid','bready','bresp','arvalid','arready','rvalid','rready','rdata','rresp']
WIDTH={'awaddr':33,'araddr':33,'wdata':32,'wstrb':4,'bresp':2,'rdata':32,'rresp':2}
def render():
    result={}
    router=(ROOT/'rtl/axi_lite_two_way.v').read_text().replace('axi_lite_two_way','axi_lite_three_way')
    for old,new in [('65:0','98:0'),('63:0','95:0'),('7:0','11:0'),('3:0] m_bresp','5:0] m_bresp'),('m_bresp,m_rresp','m_bresp,m_rresp'),('1:0] m_awvalid','2:0] m_awvalid'),('1:0] m_awready','2:0] m_awready'),("2'b01","3'b001")]:router=router.replace(old,new)
    router=router.replace('reg ah,wh,asent,wsent,write_sel,rh,rsent,read_sel;','reg ah,wh,asent,wsent,rh,rsent;reg [1:0] write_sel,read_sel;')
    router=router.replace('{wa,wa}','{wa,wa,wa}').replace('{ra,ra}','{ra,ra,ra}').replace('{wd,wd}','{wd,wd,wd}').replace('{st,st}','{st,st,st}')
    router=router.replace('s_awaddr[32:12]!=GP_BASE[32:12]',"s_awaddr[32:12]==GP_BASE[32:12] ? 0 : s_awaddr[32:12]==MOTION_BASE[32:12] ? 2 : 1")
    router=router.replace('s_araddr[32:12]!=GP_BASE[32:12]',"s_araddr[32:12]==GP_BASE[32:12] ? 0 : s_araddr[32:12]==MOTION_BASE[32:12] ? 2 : 1")
    router=router.replace(' reg ah,'," localparam [32:0] MOTION_BASE={1'b0,`PLI_MOTION_GP_MOTION_V1_BASE};\n reg ah,")
    router=router.replace('// Endpoint0 is the exact GP window; all other addresses go to DMA\'s full guard.','// Endpoint0 probe, endpoint2 motion; all other addresses go to DMA full guard.')
    result['axi_lite_three_way.v']=router
    dma=(ROOT/'rtl/dma_loopback_top.v').read_text().replace('module dma_loopback_top(','module motion_dma_lite_top '+PARAM+'(')
    dma=dma.replace('input wire clk_100m,arst_n','input wire clk_100m,arst_n').replace('output wire [31:0] loop_occupancy','output wire [31:0] loop_occupancy,\n output wire motion_irq,\n'+',\n'.join(' '+('input' if n in ['awaddr','araddr','wdata','wstrb','awvalid','wvalid','bready','arvalid','rready'] else 'output')+' wire '+(f'[{WIDTH[n]-1}:0] ' if WIDTH.get(n,1)>1 else '')+'motion_'+n for n in SIG))
    begin=dma.index('wire fifo_arst_n=');end=dma.index('assign f2p_irq=',begin)
    service='''wire [3:0] observed_step,observed_dir,observed_en,observed_valid;
wire [255:0] observed_position,observed_pulses;
wire primary_reset_released=control_rst_n && d_mm2s_prmry_reset_out_n && d_s2mm_prmry_reset_out_n;
wire memory_read_fault=d_m_axi_mm2s_rvalid && d_m_axi_mm2s_rready && (|d_m_axi_mm2s_rresp);
motion_service '''+BIND+''' motion(.clk(clk_100m),.rst_n(control_rst_n),.dma_reset_released(primary_reset_released),.dma_error(memory_read_fault),.fault(4'd0),
'''+','.join('.s_'+n+'(motion_'+n+')' for n in SIG)+''',
 .stream_data(d_m_axis_mm2s_tdata),.stream_keep(d_m_axis_mm2s_tkeep),.stream_last(d_m_axis_mm2s_tlast),
 .stream_valid(d_m_axis_mm2s_tvalid),.stream_ready(d_m_axis_mm2s_tready),.irq(motion_irq),
 .step(observed_step),.dir(observed_dir),.en(observed_en),.position_valid(observed_valid),
 .position(observed_position),.pulses(observed_pulses),.buffered_points(loop_occupancy),
 .running(),.paused(),.core_busy(),.session_valid(),.session_id(),.fifo_level(),.prepared_level(),
 .point_start(),.point_done(),.stopped(),.pulse_event(),.slot_event(),.slot_id());
assign d_s_axis_s2mm_tdata=64'd0;assign d_s_axis_s2mm_tkeep=8'd0;assign d_s_axis_s2mm_tlast=1'b0;
assign d_s_axis_s2mm_tvalid=1'b0;assign d_s_axis_s2mm_tuser=4'd0;assign d_s_axis_s2mm_tid=5'd0;assign d_s_axis_s2mm_tdest=5'd0;
'''
    dma=dma[:begin]+service+dma[end:];result['motion_dma_lite_top.v']=dma
    shared=(ROOT/'rtl/dma_shared_lite_top.v').read_text().replace('module dma_shared_lite_top(','module motion_shared_lite_top '+PARAM+'(')
    for n in SIG:
        w=WIDTH.get(n,1);shared=shared.replace(f'wire [{w*2-1}:0] m_{n};',f'wire [{w*3-1}:0] m_{n};')
    shared=shared.replace('axi_lite_two_way router','axi_lite_three_way router').replace('wire gp_irq;','wire gp_irq,motion_irq;')
    shared=shared.replace('dma_loopback_top dma_core(', 'motion_dma_lite_top '+BIND+' dma_core(')
    shared=shared.replace('.loop_occupancy(loop_occupancy),','.loop_occupancy(loop_occupancy),.motion_irq(motion_irq),'+','.join('.motion_'+n+f'(m_{n}[{2*WIDTH.get(n,1)}+: {WIDTH.get(n,1)}])' for n in SIG)+',')
    shared=shared.replace("(gp_irq ? 16'd1 : 16'd0)","(gp_irq ? 16'd1 : 16'd0) | (motion_irq ? (16'd1<<`PLI_MOTION_GP_MOTION_V1_IRQ_LINE):16'd0)")
    result['motion_shared_lite_top.v']=shared
    for old,new,childold,childnew in [('dma_gp_full_top','motion_gp_full_top','dma_shared_lite_top','motion_shared_lite_top'),('dma_gp_ps_top','motion_gp_ps_top','dma_gp_full_top','motion_gp_full_top')]:
        t=(ROOT/'rtl'/f'{old}.v').read_text().replace('module '+old+'(','module '+new+' '+PARAM+'(')
        if '`include "generated/interface_defs.vh"' not in t:t='`include "generated/interface_defs.vh"\n'+t
        t=t.replace(childold+' ',childnew+' '+BIND+' ');result[new+'.v']=t
    return {n:t.replace(',.',',\n.') for n,t in result.items()}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args()
    for n,t in render().items():
        p=ROOT/'rtl'/n
        if a.check:
            if p.read_text()!=t:raise SystemExit('stale '+n)
        else:p.write_text(t,encoding='utf-8')
