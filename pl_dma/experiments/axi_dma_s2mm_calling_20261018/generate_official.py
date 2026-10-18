"""Invoke installed TD xmlipgen on an isolated vendor-example configuration.

Input XML is edited configuration, output Verilog is exclusively xmlipgen output.
This does not claim the GUI dependency evaluator has been run.
"""
import json,re
from experiment import E,R,TD,run_td
DEMO=R.parent/'docs/Analogic/03_demo/3-2_ex_fpsoc/3_2_01_sdk_base/17_axi_DMA/soc_prj/uisrc/01_rtl/system/ip/design_0_AXI_DMA_0'

def main():
    b=E/'build/official_xml1';b.mkdir(parents=True,exist_ok=False)
    q=json.loads((R/'pl_rs485/evidence/identity_telemetry.json').read_text())['effective_s2mm_parameters']
    for name in ['Design.xml','DesignConfiguration.xml','design_0_AXI_DMA_0.xml']:
        t=(DEMO/name).read_text(encoding='utf-8').replace('design_0_AXI_DMA_0','official_s2mm').replace('DR1M90GEG484','DR1M90GEG400')
        if name=='Design.xml':
            values={k.removeprefix('AL_'):str(v) for k,v in q.items()}
            values.update(INCLUDE_MM2S_DRE='0',INCLUDE_MM2S_DRE_dis='1',INCLUDE_S2MM_DRE_dis='1',single_interface='0')
            values.update({k+'_dis':'100.000000' for k in ['S_AXI_LITE_ACLK_FREQ_HZ','M_AXI_MM2S_ACLK_FREQ_HZ','M_AXI_S2MM_ACLK_FREQ_HZ','M_AXI_SG_ACLK_FREQ_HZ']})
            for k,v in values.items():
                t=re.sub(r'(referenceId="'+k+r'">)[^<]*(<)',lambda m:m[1]+v+m[2],t)
        dest='official_s2mm.xml' if name.endswith('_0.xml') else name
        (b/dest).write_text(t,encoding='utf-8')
    script=f'''cd {{{b.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
xmlipgen -usernamed_file {{{(b/'official_s2mm.xml').as_posix()}}} -design_file {{{(b/'Design.xml').as_posix()}}} -designConfig_file {{{(b/'DesignConfiguration.xml').as_posix()}}} -component_file {{{(TD/'ip/depot/AXI_DMA_1.0/Component.xml').as_posix()}}} -mode behavior -package DR1M90GEG400
puts OFFICIAL_XMLIPGEN_COMPLETE
exit
'''
    run_td(b,script)

if __name__=='__main__':main()
