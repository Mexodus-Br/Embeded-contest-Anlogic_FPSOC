# 失败与修正记录

1. 资料读取首次尝试依赖openpyxl，环境未安装（ModuleNotFoundError）。改用Python zipfile/XML只读核对xlsx；底板PDF p14渲染后视觉核对DE与RE共线，资料本身未改动。
2. schema第一次生成Assert失败：E2E1E0十进制误写14803424。修正为14868960，保留地址pack断言，防止同类错误。
3. 第一次-g2012 RTL编译报rs485_master.v的sequence语法错误；它是SystemVerilog保留字，改名request_seq/next_request_seq，交付RTL以Verilog2005编译。
4. 直接PowerShell编译后退出1且无诊断；沿既有只读参考中验证过的process-local环境方法编写独立仿真runner（PATH/TEMP仅对子进程设置）。后续失败日志在各sim标签目录保留，不自动重试或掩盖失败。
5. sim_r1编译仍发生Windows access violation退出3221225477；自动审批后在沙箱外运行同一脚本，sim_r2完成全部测试。未用替代算法或跳过测试掩盖失败。
6. TD第一次启动不能读取Windows反斜线脚本路径（Tcl解释转义字符）。日志保留td_path_failure.log，改为Path.as_posix()传递路径后启动正常。
7. 手册/收发器页文本输出曾被Windows GBK编码的Ω字符阻断；改为stdout UTF-8后完整读取。资料内容与RTL不受影响。
8. 代码检查发现QUIET持续噪声超时原先会给禁用查询发布BUS_BUSY且重试丢失关联；修正为仅启用槽事件，重试保留sequence/request_us；增加零mask噪声暂停测试并通过。最终TD证据已重跑，旧结果不作为交付身份。
9. 加入自动源码身份清单后的沙箱复跑（sim_sim_invalid标签）主bench通过，但tb_profile编译再次访问异常3221225477，立即非零退出，未生成成功manifest。相同源码经自动审批后在sim_release目录完整通过三个bench并生成manifest，freeze_identity核对最终RTL/生成头文件与TD证据相同。
