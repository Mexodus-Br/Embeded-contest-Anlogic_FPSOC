# 多速率实现失败与修正

所有失败保留独立标签日志，不重试覆盖、不把崩溃当作通过。

1. sim_mr_compile_r1：Icarus在Windows沙箱内access violation，退出3221225477；沿已有授权与证据流程，在非沙箱本地进程运行。
2. sim_mr_legacy_r2：Verilog预处理器拒绝逗号和include指令同一行；将逗号与include分行。sim_mr_legacy_r3完整旧模块回归通过，原v1 RTL未修改。
3. sim_mr_r1：testbench task名config是Verilog保留字，编译退出79；更名apply_config。
4. sim_mr_r2/r3：混合频率验证通过，配置自检超时。诊断显示revision未变化、pending=0，配置未握手；testbench在wait(!busy)返回posedge后发配置、下一negedge立即撤销，脉冲仅半拍。改为negedge开始提交并保持完整一拍，覆盖在途重试时提交也采用同一同步规则。
5. 代码检查发现DISPATCH的request_valid需包含found，防止无到期任务时发送旧选择；在新线级测试前修正。冷复位默认profile改用与用户提交相同的RTL范围/带宽检查，超预算默认也保持禁用，不能绕过准入。

早期TD r1为调度扫描节流前的源码快照，仅保留为过程证据；最终交付须匹配release标签及新身份文件。

最终sim_mr_release在真实500000us退避参数下通过：通过注入系统时间前进至截止点验证失败续期/成功恢复，未把RTL退避缩成5000us。正式profile同时实例化10ms默认配置检查，确认相同快采频率在默认隔离下被拒绝。两组最终TD route分别setup/hold=+0.803/+0.029ns及+1.271/+0.037ns，默认和快采源码哈希一致。
