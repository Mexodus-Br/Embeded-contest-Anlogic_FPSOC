"""Publish minimal final-deliverable identity and staged acceptance status."""
from pathlib import Path
import hashlib,json,shutil,tarfile
R=Path(__file__).resolve().parents[2];D=R/'bsp/motor_test';A=R/'bsp/artifacts/motor3125';E=R/'bsp/evidence/motor3125-20261021';W=R/'bsp/work/motor3125_soc_prj'
local=json.loads((D/'IMAGE_VERIFICATION.json').read_text());assert local['status'].startswith('PASS_')
review=json.loads((D/'integration.review.json').read_text());manifest=json.loads((A/'manifest.json').read_text())
installed=json.loads((A/'image-verification.json').read_text())
for p in A.iterdir():
    if p.suffix=='.log' or p.name in ['manifest.json','SHA256SUMS','image-verification.json']:
        shutil.copyfile(p,E/p.name)
with tarfile.open(W/'vm-input.tar') as t:
    (E/'unit_scope.cpp').write_bytes(t.extractfile('bsp/scope/unit_scope.cpp').read())
assert 'bench_feasible(28200,4)' in (E/'unit_scope.cpp').read_text()
status={'frozen_source_isolation':'PASS','rtl_pulse_and_stop':'PASS','real_dma_gp':'PASS',
 'arm_compilation':'PASS','host_parser_codec_and_duration_bounds':'PASS',
 'routed_100mhz':'PASS','matched_boot_dtb_rootfs':'PASS','local_image_transfer_and_root_partition':'PASS',
 'sd_write_readback':'NOT_EXECUTED','cold_boot':'NOT_EXECUTED','arm_board_execution':'NOT_EXECUTED',
 'physical_gpio':'NOT_EXECUTED','motor_operation':'NOT_EXECUTED','physical_stop':'NOT_EXECUTED'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources=[D/'CONFIG.json',D/'delta_scope.cpp',D/'prepare.py',D/'build_hardware.py',D/'package.sh',D/'stage_vm.py',E/'system_wrapper.v',E/'gpio.adc',E/'gpio.sdc',E/'ps-properties.tcl']
delivery={'purpose':'MOTOR3125 isolated motor bench pulse comparison; not a calibrated machine release',
 'source_baselines':{'pl_gpio':'df17b4ebd6e358d6626a227b5c0c152c1f6cb9ed','bsp':'db5f75c','image_packager':'0a4ca51'},
 'profile':review['profile'],'image_path':'bsp/artifacts/motor3125/sdcard.img',
 'image_sha256':local['sd_image_sha256'],'image_bytes':local['bytes'],'root_partuuid':local['root_partuuid'],
 'final_artifacts':manifest['files'],'installed_modules_and_programs':installed['installed_file_sha256'],
 'direct_source_sha256':{p.relative_to(R).as_posix():sha(p) for p in sources},
 'hardware':review,'acceptance':status,'board_actions_performed':False,'serial_opened':False,
 'buffer_state':'No board client loaded or DMA buffers allocated by this task; existing board state was not taken over',
 'limitations':['reference speed2; physical device speed unconfirmed','31.25us at driver input and motor behavior unmeasured',
 'MOT1 profile does not encode pulse parameters; cold boot identity plus measured pulse width required',
 'HOLD ignores EN: DISABLE is not physical driver disable','Golden ratio4.5/microsteps16 are reference values; actual mechanics and driver microsteps unconfirmed',
 'independent HP1 telemetry, RS485, safety/HOME and Web are excluded from this minimal scope-derived image']}
(D/'DELIVERY.json').write_text(json.dumps(delivery,indent=2)+'\n')
lines=['# MOTOR3125 构建与验收 — 2026-10-21','',
 '独立scope派生测试镜像已生成并完成Windows文件校验。未写实体SD、未打开COM4、未执行电机运动。',
 '', '| 项目 | 结果 |','|---|---|']
lines += ['| '+k+' | '+v+' |' for k,v in status.items()]
lines += ['', '镜像：`bsp/artifacts/motor3125/sdcard.img`（536870912B）。',
 'SHA256：`'+local['sd_image_sha256']+'`。根分区PARTUUID：`'+local['root_partuuid']+'`。',
 '', '100MHz、参考speed2、实际16线程；gate −1.878/0ns，place +2.437/0ns，route **+0.087/+0.020ns**（setup/hold）；双corner覆盖99.99%。原20ns异步GPIO预算不变，不能当作驱动输入同步签核。',
 '', '| 最终资源 | 已用/总量 | 占比 | 剩余 |','|---|---:|---:|---:|',
 '| LUT6 |13257/52480|25.26%|39223|','| Slice |15469/52480|29.48%|37011|',
 '| Slice寄存器 |13586/104960|12.94%|91374|','| ERAM |16/280|5.71%|264|','| DSP |4/240|1.67%|236|',
 '| GCLK |1/32|3.13%|31|','| SCLK |6/72|8.33%|66|','| IO |10/126|7.94%|116|',
 '', '设计寄存器总数13595=Slice13586+PAD9；九个输出全部OREG，另一个IO为H16时钟。相比旧scope：LUT6 +206、Slice +134、设计寄存器 −21；不与遥测或安全完整顶层叠加计算。',
 '', 'check_timing除已知两类dummy（ERAM未使用reset输出、LSLICE未使用物理输出）外14项表中其余为0；无critical，详细布线overflow=0、eco open net=0。DRC工具把检查结果写入build.log，未生成独立route.drc；原文摘录见证据中的route-drc-excerpt.log。保留厂家/旧基线告警与DTC告警，未屏蔽诊断。',
 '', '仿真：内核239890项、H=3125/L≥3125、282µs精确点时长、281µs拒绝及四种STOP相位；真实MM2S/GP5482项、三次72B读取共27个HP beat、无S2MM写入、10ms往返1/124/123步及STOP各1步。500ms表仅为逻辑预测。ARM程序、匹配模块与host边界/codec检查通过；新镜像ARM板上执行未进行。',
 '', '保留失败：Windows路径分隔导致首次TD脚本找不到；Icarus沙箱访问异常（沙箱外通过）；旧DMA夹具仅等600拍，违反新低间隔，改夹具等待4000拍后通过；ARM首次遗漏原生成头，补齐后通过；TD首轮多run项目把线程恢复auto/实际22，已停止，改single_run并在打开项目后设置/读回16后完整重跑；HPF全宏比较首次检测到两项导出时间变化，确认仅生成/导出时间后显式排除这两项，实际PS宏完全一致。原始失败、td日志及logw均保留，不哈希日志。',
 '', 'FSBL/BOOT/DTS/rootfs由匹配HPF生成；DDR1GiB/32bit/1333MT/s/1.35V及存储/时钟基线保持。图像内文件、文件系统、地址/IRQ和本地完整SD文件及嵌入根分区校验通过。原scope镜像未改。',
 '', '本次未装载板端模块或分配板端buffer，未接管现有板端状态；COM4始终未打开。测试必须由用户按README显式启动，先核对配套启动身份和31.25µs实测波形；HOLD下EN不失能，保留独立切电。参考机械比4.5及16细分不等于实物确认。']
(D/'BUILD_STATUS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Final delivery and staged status published')
