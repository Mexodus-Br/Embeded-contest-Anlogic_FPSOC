"""Byte-based actual build / real compiled source / PS and contract audit."""
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
H=Path(__file__).resolve().parent
R=H.parents[1]
P=H/'frozen/pl'
out={'hashes_computed':False,'real_compiled_scenarios':{},'eol_only':[],'explicit_header_expansions':[],
     'candidate_identity':'rtl37_candidate_r5 actual rtl_path38 inputs, not product HEAD'}
allowed={'rs485_gp_bridge.v','rs485_gp_regs.v','rs485_latest_cache.v','rs485_multirate.v','rs485_telemetry.v'}
allowed|={'interlock_'+x+'.v' for x in ['motion_dma_lite_top','rs485_gp_full_top','rs485_gp_ps_top','rs485_shared_lite_top']}
allowed.add('axis_loop_fifo.v')
flattened={'axi_lite_six_way.v','axi_lite_three_way.v','axi_lite_two_way.v','dma_gp_full_top.v',
 'dma_lite_guard.v','dma_loopback_top.v','dma_shared_lite_top.v','motion_dma_lite_top.v',
 'motion_gp_full_top.v','motion_gp_ps_top.v','motion_shared_lite_top.v','rs485_gp_full_top.v',
 'rs485_gp_ps_top.v','rs485_probe_time_regs.v','rs485_shared_lite_top.v','telemetry_dma_guard.v','telemetry_dma_lite_top.v'}
def definitions(s):
    return dict(re.findall(r'^`define (PLI_\w+)\s+([^\r\n]+)',s,re.M))
for scenario in ['protection','watchdog','feedback_timeout']:
    b=R/'pl_safety/build'/('rtl37_real_r2_'+scenario)
    inv=json.loads((b/'compiled_sources.json').read_text())
    count=0
    for item in inv['direct_byte_verified_source_copies']:
        compiled=Path(item['compiled_copy']);target=P/'gp'/compiled.name
        if not target.is_file():continue
        a,c=compiled.read_bytes(),target.read_bytes()
        if a!=c:
            if compiled.name in flattened:
                # Historical actual BSP copies explicitly inline the old generated
                # interface header. Verify the exact expansion and every used macro
                # against the real simulator's include, without hiding token changes.
                text=c.decode().replace('\r\n','\n')
                start=text.index('// Generated from schema.json SHA256')
                end=text.index('`endif',start)+len('`endif')
                inline=definitions(text[start:end])
                current=definitions((b/'inc/generated/interface_defs.vh').read_text())
                body=text[:start]+'`include "generated/interface_defs.vh"'+text[end:]
                body=body.replace('`include "generated/interface_defs.vh"\n\n','`include "generated/interface_defs.vh"\n',1)
                assert body.encode()==a.replace(b'\r\n',b'\n'),compiled
                used=set(re.findall(r'`(PLI_\w+)',body))
                for macro in used:
                    assert inline[macro].lower()==current[macro].lower(),(compiled,macro)
                out['explicit_header_expansions'].append({'scenario':scenario,'file':compiled.name,'used_macro_values_matched':len(used)})
            else:
                assert compiled.name in allowed and a.replace(b'\r\n',b'\n')==c.replace(b'\r\n',b'\n'),compiled
                out['eol_only'].append([scenario,compiled.name])
        count+=1
    assert count>=40,count
    out['real_compiled_scenarios'][scenario]={'matched_source_files':count,'result':
        json.loads((R/'pl_safety/evidence'/('rtl37_real_r2_'+scenario)/'result.json').read_text())['passed']}
    assert out['real_compiled_scenarios'][scenario]['result']
for p in (R/'pl_safety/optimization/reset_path_20261020/rtl37_candidate_r5').glob('*.v'):
    assert p.read_bytes()==(P/'gp'/p.name).read_bytes(),p
out['candidate_override_files_matched']=19
def values(p):
    result={}
    for e in ET.fromstring(p.read_text(encoding='utf-8')).iter():
        if e.tag.endswith('configurableElementValue'):result[e.get('referenceId')]=(e.text or '').strip()
    return result
rel='system/ip/system_ARM_Processor_System_0/Design.xml'
old=values(R/'bsp/work/scope_soc_prj'/rel);new=values(P/rel)
assert old and new
changed={k:[old.get(k),new.get(k)] for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}
assert set(changed)<={'Slave_AXI_HP1_Interface','Slave_AXI_HP1_DATA_WIDTH'},changed
assert new['DDRC_IO_VOL']=='1.35' and new['Slave_AXI_HP0_Interface']=='1' and new['Slave_AXI_HP1_Interface']=='1'
out['ps']={'changed_from_scope':changed,'unchanged_parameter_count':len(old)-len(set(changed)&old.keys()),
           'ddr_io_voltage':new['DDRC_IO_VOL'],'native_properties':{k:v for k,v in new.items() if any(x in k for x in ['DDRC','DDR3'])}}
out['original_route']=json.loads((R/'pl_safety/build/rtl_path38/route_summary.json').read_text())
text=(P/'system/hdl/system_wrapper.v').read_text()
assert '.CONFIG_PROFILE(2)' in text
assert (P/'system/hdl/system_wrapper.v').read_bytes()==(H/'hardware/system/hdl/system_wrapper.v').read_bytes()
assert (P/'gp/gp.sdc').read_bytes()==(H/'hardware/gp/gp.sdc').read_bytes()
assert 'create_clock -name board_100m -period 10' in (P/'gp/gp.sdc').read_text()
out['sdc_unchanged']=True
out['gates']=['SYN-5066 protected S2MM IP','real speed grade',
              'external IO delays and input electrical qualification','production HOME approval',
              'interrupted HP1 DDR drain qualification']
out['cdc_independent_release_gate_removed']=True
out['cdc_policy']='2026-10-21 user decision: retain engineering checks and specific defect tracking; no standalone CDC/synchronizer qualification gate; other gates unchanged'
out['passed_input_identity']=True
(H/'evidence/input-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS actual candidate, real compiled copies and PS/DDR/storage baseline audit')
