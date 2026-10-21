# 本轮暂停点（2026-10-21，Asia/Taipei）

## 最新政策：移除CDC独立门禁

2026-10-21用户决定：CDC及同步器资格不再作为独立发布、上板或阶段验收阻塞项，保留工程检查、告警和已知问题记录。具体缺陷按实际影响处理；其他门禁、当次部署/运动授权和signoff=false不变。详细见REVIEW.md与PHASE0_CONSTRAINTS.md顶部。本段覆盖下文历史记录中的CDC独立资格要求；未改RTL/约束或重建镜像。

## 最新：离线启动镜像生成

用户追加要求生成镜像并免除本次setup>1ns条件后，已生成一致bit/HPF/新FSBL/新HPF配套禁用DTB/wifi1/rootfs/SD文件，完成实际镜像分区/启动文件/rootfs及FSBL复位代码审核并下载校验。本机`artifacts/boot_candidate_v1/sdcard.img`，根`f0391b66-02`，详细身份与复现见BOOT_CANDIDATE.md。新HPF的原DDR/存储初始化与已验收scope保持，仅HP1增加复位释放/64bit配置。

本次只免除>1ns生成条件，其余门禁继续开放，signoff=false。未写卡/实板启动或申请DMA，B/C未执行，D锁定。下文“未生成”均为历史暂停点，以上述更新及ACCEPTANCE.md为当前状态。

## 布线完成后的复核更新

用户通知后已完成离线复核：日志2026-10-21 14:23:13结束并含完整完成标记；最终100MHz/10ns setup +0.078ns、hold +0.020ns，各组负违例端点均0。Slice36670、LUT6 28802、Slice FF37617另PAD9、ERAM69、DSP6、IO17；174份未适配冻结输入逐字节一致，原SDC及PS属性保持，四输入球位读回正确，16线程实际读回5次。

`finalize.py`经复核后已执行，生成RESOURCE_REPORT.md、delivery.json和原样最终报告。报告/日志/数据库未计算哈希。最终SDC已有的安全输入false-path保持原状，不新增例外；CDC与同步器资格仍需独立证明。report_route_status执行完成但未产生独立route.drc，原stdout摘录保存于reports/route-status-excerpt.txt，不把它冒称独立DRC清洁证据。

无负STA通过；严格setup>1ns失败；完整发布signoff仍false。离线软件/rootfs已生成，但BOOT/HPF/FSBL/bit/SD未生成，B/C未执行，D锁定。REVIEW.md中集中列出的厂商/实物资格输入仍待提供，保持门禁，不启动新的布线、板端或运动任务。

以下为上轮原始暂停记录，仅供追溯，当前状态以上述更新及ACCEPTANCE.md为准。

## 上轮原始暂停记录

按用户要求提供只读进度查询脚本后结束本轮，不等待布线。完整PF2实际顶层仍在`hardware/run.tcl`执行；最后观察为route后的Post Detailed Routing修复阶段。最终HIGH优化、最终100MHz报告及完成标记尚未确认；中间负WNS不能当作最终失败或通过。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Works\Embedded_contest\dev\integration\controlled_v1_20261021\status.ps1
# 结构化查询：在上述命令后加 -Json
```

脚本仅查询本任务TD进程和文件，不启动/终止流程、不哈希日志、不触碰板卡。若显示STOPPED_OR_NOT_VISIBLE且没有完成标记，保留现场并交回检查，不自动重跑。日志更新时间可能在长计算期间暂时不变，不能据此判定挂死。TD由现有主机命令会话运行；请保留该会话和主机电源，不关闭或重启相关进程。本轮不建立定时查询或通知。

用户完成布线后通知，再审核`INTERLOCK_FULL_TOP_COMPLETE`、原100MHz有效约束、最终setup/hold、完整运动资源及现存告警。`finalize.py`尚未执行，`RESOURCE_REPORT.md`和`delivery.json`是后续生成项，不是本轮已有交付物。不得依据脚本的完成状态自动运行finalize、生成启动链或放行上板。

已完成：独立冻结源码/构建来源、七窗口/资源审查、匹配wifi1的七模块及受控诊断程序重建、禁用DT预览、实际离线ext4内容审计。原STA/HTTP回归、扩展HTTP、驱动79项、R5S2 23项和七路译码460项等证据位于本目录；详细通过范围见ACCEPTANCE.md。PROFILE0缩减逻辑尝试已判废并原样保留，不作为最终候选。

未完成：最终P&R审查和资源/时序交付清单；一致bit/HPF/FSBL/BOOT/最终DTB/SD链；阶段B、C实板验收；任何机械运动。安全IO电气/实物接线、实际速度等级、SYN-5066厂商结论、CDC/同步器/IO约束、生产HOME及DDR静止等门禁继续保留。

板卡、COM4、服务、DMA和buffer当前实际状态未知；本任务没有连接板卡/串口、启动设备控制服务、申请DMA、写卡或执行运动。保留当前已验收Wi-Fi卡、原镜像和scope回退。已生成的rootfs与禁用DT预览不能写卡当成完成的启动镜像。
