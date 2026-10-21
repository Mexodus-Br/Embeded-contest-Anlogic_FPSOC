"""Collect final actual reports and a strictly limited delivery manifest.

No hashing of logs, timing/area reports, databases, evidence trees or intermediates.
Only the offline rootfs delivery and explicitly named direct source files.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
from datetime import datetime,timezone,timedelta

H=Path(__file__).resolve().parent
P=H/'hardware'
log=(P/'run.log').read_text(errors='replace')
assert 'INTERLOCK_FULL_TOP_COMPLETE' in log,'Final actual top still running'
assert 'RTL_POST_ROUTE_HIGH_BEGIN' in log and 'RTL_POST_ROUTE_HIGH_END' in log
assert len(re.findall(r'Number of Thread = 16',log))>=4
assert (P/'system/hdl/system_wrapper.v').read_bytes()==(H/'frozen/pl/system/hdl/system_wrapper.v').read_bytes()
assert (P/'gp/gp.sdc').read_bytes()==(H/'frozen/pl/gp/gp.sdc').read_bytes()


def timing(path):
    text=path.read_text()
    s=re.search(r'SWNS:\s*([+-]?[\d.]+)ns',text)
    h=re.search(r'HWNS:\s*([+-]?[\d.]+)ns',text)
    return {'setup_ns':float(s[1]),'hold_ns':float(h[1])}


stages={name:timing(P/file) for name,file in [('gate','gate.timing'),('place','place.timing'),
    ('route_before_high','route_before_physopt.timing'),('route','route.timing')]}
area=(P/'route.area').read_text()
resources={}
for name,pattern in {'lut6':r'^#lut6\s+(\d+)\s+out of\s+(\d+)',
 'slice':r'^#slice\s+(\d+)\s+out of\s+(\d+)',
 'slice_ff':r'^\s+#slice reg\s+(\d+)\s+out of\s+(\d+)',
 'eram':r'^#eram\s+(\d+)\s+out of\s+(\d+)',
 'dsp':r'^#dsp\s+(\d+)\s+out of\s+(\d+)',
 'io':r'^#IO\s+(\d+)\s+out of\s+(\d+)',
 'gclk':r'^#gclk\s+(\d+)\s+out of\s+(\d+)',
 'sclk':r'^#sclk\s+(\d+)\s+out of\s+(\d+)',
 'pll':r'^#pll\s+(\d+)\s+out of\s+(\d+)',
 'lclk':r'^#lclk\s+(\d+)\s+out of\s+(\d+)',
 'mlclk':r'^#mlclk\s+(\d+)\s+out of\s+(\d+)',
 'ioclk':r'^#ioclk\s+(\d+)\s+out of\s+(\d+)'}.items():
    m=re.search(pattern,area,re.M);assert m,(name,pattern)
    used,total=map(int,m.groups())
    resources[name]={'used':used,'total':total,'percent':round(100*used/total,2),'remaining':total-used}
resources['pad_ff']={'used':int(re.search(r'^\s+#pad reg\s+(\d+)',area,re.M)[1])}
check=(P/'route.check').read_text()
invalid=int(re.search(r'checking invalid constraint\((\d+)\)',check)[1])
loops=int(re.search(r'checking combinational loops\((\d+)\)',check)[1])
coverage=re.search(r'STA coverage\s*:\s*([\d.]+)%',(P/'route.timing').read_text())[1]
functional=(resources['eram']['used']==69 and resources['dsp']['used']==6 and resources['pad_ff']['used']==9)
sta=stages['route']['setup_ns']>=0 and stages['route']['hold_ns']>=0
violations=[int(x) for x in re.findall(r'(\d+) Viol Endpoints',(P/'route.timing').read_text())]
assert violations,'Missing per-group final STA endpoint statistics'
sta=sta and all(x==0 for x in violations)
source_time=datetime.now(timezone(timedelta(hours=8))).isoformat()
result={'completed_at_asia_taipei':source_time,'flow_completed':True,
    'source_candidate':'rtl37_candidate_r5 / actual rtl_path38 frozen inputs',
    'changes':'four explicit safety input locations only; full PROFILE2 retained, not approved for motion',
    'full_functional_resource_configuration_retained':functional,
    'threads':16,'thread_readbacks':len(re.findall(r'Number of Thread = 16',log)),
    'clock_mhz':100,'period_ns':10,'reference_speed':2,'actual_speed_grade_verified':False,
    'sta_coverage_percent':float(coverage),'stages':stages,'resources':resources,
    'no_negative_setup_hold':sta,'strict_setup_gt_1ns':stages['route']['setup_ns']>1,
    'per_group_negative_endpoint_counts':violations,
    'invalid_constraints':invalid,'combinational_loop_categories':loops,
    'sdc_byte_unchanged':True,'syn_5066_present':'SYN-5066' in log,
    'standalone_route_drc_created':(P/'route.drc').exists(),'signoff_pass':False,
    'bit_hpf_boot_sd_generated':False,'hashes_computed_for_reports_or_databases':False}
(H/'evidence/final-hardware.json').write_text(json.dumps(result,indent=2)+'\n')
reports=H/'reports';reports.mkdir(exist_ok=True)
for name in ['route.timing','route.area','route.check']:
    shutil.copyfile(P/name,reports/name)
fixed=H/'final_inputs';fixed.mkdir(exist_ok=True)
shutil.copyfile(P/'system/hdl/system_wrapper.v',fixed/'system_wrapper.v')
shutil.copyfile(P/'gp/gp.adc',fixed/'gp.adc')
rt=(P/'route.timing').read_text()
start=rt.index('Max Paths\n') if 'Max Paths\n' in rt else rt.index('Max Paths')
worst=rt[start:rt.index('Delay Type',start)]
old=json.loads((H/'evidence/input-audit.json').read_text())['original_route']
old['resources'].update(gclk=1,sclk=6,pll=0,lclk=0,mlclk=0,ioclk=0)
rows=[]
for name in ['lut6','slice','slice_ff','eram','dsp','io','gclk','sclk','pll','lclk','mlclk','ioclk']:
    v=resources[name];before=old['resources'].get(name)
    delta='' if before is None else f'{v["used"]-before:+d}'
    rows.append(f'|{name}|{before if before is not None else "参考见原报告"}|{v["used"]}|{v["total"]}|{v["percent"]:.2f}%|{v["remaining"]}|{delta}|')
stage_rows='\n'.join(f'|{k}|{v["setup_ns"]:+.3f}|{v["hold_ns"]:+.3f}|' for k,v in stages.items())
rejected=H/'hardware_profile0_rejected'
text=f'''# 最终实际完整顶层资源与时序

采集时间：{source_time}。本报告对应`hardware/`的完整native PS/GP/双HP/九GPIO/SAF2/R5S2顶层，来自冻结rtl_path38 / rtl37_candidate_r5，只固定四路安全输入球位，保留完整PROFILE2资源/功能配置。PROFILE2仍未批准用于真实运动。

**最终名义route setup {stages['route']['setup_ns']:+.3f}ns、hold {stages['route']['hold_ns']:+.3f}ns。无负STA={sta}；严格setup>1ns={result['strict_setup_gt_1ns']}；发布signoff=false。**

|资源|原rtl_path38|本次最终|总量|已用|余量|增量|
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

PAD FF={resources['pad_ff']['used']}；完整功能资源配置保持检查={functional}。本次没有内部RTL、FIFO容量、IP参数、时钟/复位语义或生产功能变更，不将放置/布线差异说成新的逻辑优化成果。

|阶段|setup ns|hold ns|
|---|---:|---:|
{stage_rows}

原100MHz/10ns SDC及PS属性约束保持，最终报告清除内部优化预算；没有新增false-path、multicycle或放宽周期。TD明确16线程，实际读回{result['thread_readbacks']}次。参考DR1M90GEG400/speed2，实际速度等级未核验。STA覆盖{coverage}%；默认不确定性保留。

最终首条最差setup路径（完整路径和cell/net延迟见同目录reports/route.timing）：

```text
{worst.rstrip()}
```

check_timing：invalid约束{invalid}类，组合环{loops}类；其余dummy/no-input-delay/no-output-delay及未约束路径必须按reports/route.check逐项审查。SYN-5066仍存在={result['syn_5066_present']}，不得用后续“0 issue(s)”覆盖综合删除内部驱动的警告。独立route.drc文件生成={result['standalone_route_drc_created']}；缺失时不宣称独立DRC文件清洁。

四路实际位置须在reports/route.area中读回V7/U9/U8/V11，九输出保持Y12/Y13/T9、U10/T5/U5、V6/W6/U7。外部上拉、实物电气/IO delay、CDC/同步器及速度等级等仍未资格确认；当前STA不解除这些门禁。全网data/CE/reset/clock物理扇出审计未关闭，不据最差路径Max Fanout代表全网高扇出已解决。

## 保留的失败配置尝试

`hardware_profile0_rejected/`完整保留。该尝试将未批准生产PROFILE0接入顶层，工具因配置资格为常量删除部分运动逻辑和九路输出寄存器；虽然route为+1.282/+0.020ns，但只有Slice26402、ERAM57、DSP2、PAD FF0，GPIO最大延迟约束无效1类。它不构成完整功能系统的时序通过，不用于本候选比较或发布。最终已恢复原完整PROFILE2并重新独立完成全流程。

原rtl_path38的+0.032/+0.020ns、Slice36694/ERAM69/DSP6及其>1ns失败记录保持。bit/HPF/FSBL/BOOT/SD未生成，没有上板或运动验收。
'''
(H/'RESOURCE_REPORT.md').write_text(text,encoding='utf-8')
transfer=json.loads((H/'evidence/rootfs-transfer.json').read_text())
assert transfer['vm_to_windows_match']
assert (H/'artifacts/rootfs-offline.ext4').stat().st_size==transfer['bytes']
scope=['safety/bsp_saf2_diag.c','safety/saf2_diag.c','safety/safety_uapi.h',
 'frozen/software/bsp/telemetry/client/bsp_rs485.c',
 'frozen/software/bsp/wifi/http/server.py','frozen/software/bsp/wifi/http/export.py',
 'frozen/software/bsp/wifi/driver.sh','frozen/software/bsp/wifi/sta.sh',
 'frozen/software/pl_interface/schema.json','final_inputs/system_wrapper.v','final_inputs/gp.adc']
hashes={'artifacts/rootfs-offline.ext4':{'sha256':transfer['sha256'],'bytes':transfer['bytes']}}
for name in scope:
    data=(H/name).read_bytes();hashes[name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
delivery={'candidate':'controlled_v1_20261021','status':'OFFLINE_CANDIDATE_RELEASE_BLOCKED',
 'engineering_release_complete':False,'offline_software_candidate_assembled':True,
 'rootfs_generated':True,'boot_chain_generated':False,'sd_image_generated':False,
 'new_candidate_board_booted':False,'no_motor_board_accepted':False,'mechanical_motion_authorized':False,
 'full_top_pnr_completed':True,'hardware':result,'software':json.loads((H/'evidence/software-audit.json').read_text()),
 'hash_scope':'ONE final offline rootfs and eleven named direct sources only. No logs, databases, evidence tree or intermediate hashes.',
 'files':hashes,'rollback':'Existing accepted Wi-Fi SD unchanged; scope rollback retained.',
 'board_serial_services_dma_buffers':'Not inspected by this task; no board connection, module loading or DMA allocation by this task.'}
(H/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print('Collected full-top final reports; STA',stages['route'],'signoff remains false; minimal delivery manifest written')
