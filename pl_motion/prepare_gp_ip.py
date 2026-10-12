"""Stage the unmodified installed TD converter library; never use a substitute model.

The instantiated TD IP is parameterized in gp_control_top.v using schema widths.
This direct vendor-RTL flow avoids copying an old AXI4/ID13 example wrapper.
"""
import argparse,hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def prepare(td_root=None):
    td=Path(td_root) if td_root else Path(shutil.which('td_commands_prompt')).resolve().parents[1]
    ip=td/'ip/depot/AXI_Protocol_Converter_1.0'
    src=ip/'AXI_MM/RTL/axi_protocol_converter_merge.v'
    b=ROOT/'build/gp_ip';b.mkdir(parents=True,exist_ok=True)
    dst=b/src.name;dst.write_bytes(src.read_bytes())
    schema=ROOT.parent/'pl_interface/schema.json'
    p=json.loads(schema.read_text(encoding='utf-8'))['gp_control_profiles']['gp_control_probe_v1']
    if p['converter']['input_protocol']!='AXI3' or p['converter']['output_protocol']!='AXI4-Lite':
        raise RuntimeError('frozen converter profile changed')
    manifest={'tool_root':str(td),'library_source':str(src),'staged_source':str(dst),
              'library_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
              'component_sha256':hashlib.sha256((ip/'Component.xml').read_bytes()).hexdigest(),
              'schema_sha256':hashlib.sha256(schema.read_bytes()).hexdigest(),
              'instance':'gp_control_top/converter','generation':'direct parameterized installed vendor RTL; not wizard-generated XML',
              'parameters':{'AL_US_AXI_PROTOCOL':1,'AL_DS_AXI_PROTOCOL':2,'AL_AXI_ADDR_WIDTH':p['address']['address_width'],
                            'AL_AXI_DATA_WIDTH':p['address']['data_width'],'AL_AXI_ID_WIDTH':p['address']['id_width'],
                            'AL_AXI_SUPPORTS_WRITE':1,'AL_AXI_SUPPORTS_READ':1,'AL_AXI_SUPPORTS_USER_SIGNALS':0}}
    (b/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return dst,manifest

def audit_ps(path):
    """Read actual regenerated PS HDL; GUI/XML enable flags alone are not proof."""
    path=Path(path).resolve();text=path.read_text(encoding='utf-8')
    ports={}
    for direction,hi,lo,name in re.findall(r'\b(input|output)\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*[,\n)]',text):
        ports[name]={'direction':direction,'width':int(hi)-int(lo)+1 if hi else 1}
    required={'master_gp0_axi_aclk':('input',1),'f2p_irq':('input',16),'p2f_rst0_n':('output',1)}
    for suffix,width in [('awaddr',33),('araddr',33),('awid',12),('arid',12),('awlen',4),('arlen',4),
                         ('awsize',2),('arsize',2),('awlock',1),('arlock',1),('wdata',32),('wstrb',4)]:
        required['master_gp0_axi_'+suffix]=('output',width)
    for suffix,width in [('bid',12),('rid',12),('rdata',32)]:required['master_gp0_axi_'+suffix]=('input',width)
    for name,(direction,width) in required.items():
        if ports.get(name)!={'direction':direction,'width':width}:raise RuntimeError('Actual PS port differs: '+name)
    if 'master_gp0_axi_wid' in ports:raise RuntimeError('PS WID now exists; reevaluate ownership wrapper')
    if 'assign f2p_irq_TB[15:0] = f2p_irq;' not in text:raise RuntimeError('PS IRQ low-16 binding differs')
    result={'status':'ACTUAL_GENERATED_PS_HDL_PORTS_CHECKED_NOT_BOARD_VERIFIED','path':str(path),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'ports':{n:ports[n] for n in required},
            'wid_present':False,'adapter':'gp_ps_control_top: SIZE2/LOCK1 zero extension; serialized AW-ID ownership supplies internal WID',
            'reset':'p2f_rst0_n connected to PS p2f_clk0_rst_n; boot release still BSP responsibility',
            'irq':'f2p_irq[15:0] directly feeds macro; GIC INTID114/SPI82 remains board/HPF validation pending'}
    (ROOT/'GP_PS_PORTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--td-root');ap.add_argument('--ps-rtl');args=ap.parse_args()
    print(json.dumps(prepare(args.td_root)[1],indent=2))
    if args.ps_rtl:print(json.dumps(audit_ps(args.ps_rtl),indent=2))
