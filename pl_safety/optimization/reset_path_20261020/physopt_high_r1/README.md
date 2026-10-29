# 用户指定的一次 HIGH 布线后优化

2026-10-20 21:58（Asia/Taipei）收尾：用户宣告本轮失败，已核实进程身份后停止本轮TD；
worker已写出`flow_completed=false`、`signoff_pass=false`并退出，一次性任务定义已自行清理。
运行约69分钟，最后日志中间SWNS为−0.524ns，未产生本次最终route时序/资源报告，不能将
该中间值当作最终结果。原候选21最终setup −1.339ns、hold +0.020ns仍为最后完整结果。
输入数据库、约束副本及运行日志全部保留；`user_failure.json`说明主动终止原因，
`result.json`中的非零退出断言是此次停止所致，不据此判断为工具自然崩溃。
不重跑、不启动新候选、不回退RTL、不声明通过或可部署。

输入：`pl_safety/build/reset_path21/route.db`，最终原约束setup −1.339ns、hold +0.020ns。
输出：`pl_safety/build/reset21_physopt_high_r1/`，原数据库及约束不覆盖，不生成bit或镜像。
命令仅为 `phys_opt -post_route -effort high`，显式16线程并在导入后再次设置、读回。

本次由Windows Task Scheduler零触发器的一次性隐藏任务运行，直接父进程为系统服务，
不依赖聊天进程存活。完成后worker删除本次任务定义，保留全部结果和日志，不自动重跑。

在工作区PowerShell查询：

```powershell
& .\pl_safety\optimization\reset_path_20261020\physopt_high_r1\status.ps1
& .\pl_safety\optimization\reset_path_20261020\physopt_high_r1\status.ps1 -Watch
```

`-Watch`每5秒只读查询；Ctrl+C只退出查询。脚本显示实际命令是否进入、16线程读回、
任务/进程状态及日志尾部；完成后显示setup/hold、资源变化和结果路径。
`COMPLETED`表示流程完成，不表示时序/安全发布通过，须另看`timing_target_met`。

原约束下最终setup严格>1ns且hold>=0才满足专项时序目标；独立CDC/诊断、SYN-5066、
实物/BSP/板测等门禁仍保留。用户要求本轮确认启动后结束，由用户在完成后通知继续。
