# 候选16后台运行与完成检查

当前运行：2026-10-20 13:43已确认resume_pnr_r2进入place，16线程。
由Windows任务服务启动一次性按需任务Codex-PL16-PnR-20261020-R2，零触发器，
驱动PID15336，父进程svchost.exe；不依赖聊天启动进程，完成后自行删除任务定义。
status.ps1通过active_run.json选择当前恢复尝试，并核对PID及启动时间。
进程不在且没有摘要时明确报告中断，不冒称成功。真实IP三个场景此前已全部通过，
本轮逐字节核对源码/头文件与原gate工程一致后复用，不重复占用Questa。
没有部署、bitgen、自动ENABLE/START或其他聊天/session操作。

在工作区PowerShell运行只读检查：

```powershell
cd D:\Works\Embedded_contest\dev
.\pl_safety\optimization\interlock_candidate16\status.ps1
```

结果含义：

- RUNNING：后台驱动仍在，没有完成摘要。
- TD flow COMPLETED + timing target PASSED：TD完整结束且原100MHz route setup>1ns、hold>=0。
- TD flow COMPLETED + timing target FAILED：布局布线流程完成，但时序验收失败。
- FAILED / INTERRUPTED：工具失败或进程已退出且无完成摘要；查看失败字段与日志。
- All background work finished：TD与串行真实IP验证均已结束；其passed同时要求时序及
  三个实际场景通过，但仍不表示最终数据库审计、资源报告复核或发布签核已经完成。

持续查看TD日志（Ctrl+C只退出查看）：

```powershell
Get-Content .\pl_safety\build\interlock_route16\resume_pnr_r2.log -Tail 20 -Wait
```

固定结果路径：

- 当前TD完整结束/失败摘要：pl_safety/build/interlock_route16/resume_pnr_r2_summary.json。
- 当前TD日志：同目录resume_pnr_r2.log。
- 原约束最终STA与资源：同目录route.timing、route.area；place或budget报告不代替最终STA。
- 当前后台总体结果：本目录launch_r3/workflow_result.json。
- 真实系统验证结果：本目录launch_r1/real_result.json及所列evidence目录。
- 当前启动身份：本目录launch_r3/process.json、task.json及started.json；driver.log
  和结束后task_cleanup.json也位于同目录。
- 原run.log/launch_r1为异常中断历史；resume_pnr_r1.log/launch_r2为发现仍附于受管
  作业后主动切换任务服务的尝试，故保留失败摘要；均不覆盖。active_run.json指向当前r2。

summary.passed表示TD流程完成；必须另看timing_pass。未生成summary不表示仍在运行，
应与进程身份和日志更新一起判断。最终资源/物理/CDC只读审计及交接/提交仍由后续回合
完成。本轮原约束、16线程及所有失败/中断证据保留，不计算日志或中间DB哈希。
