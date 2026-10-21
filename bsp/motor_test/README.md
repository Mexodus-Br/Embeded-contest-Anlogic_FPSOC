# MOTOR3125 独立脉宽对照镜像

已构建镜像：[sdcard.img](../artifacts/motor3125/sdcard.img)，512MiB，根PARTUUID`f330c1cf-02`。SHA256为`f9fbe564a5cec7662c2fd9267f5ce437db0d5f3097e6e41eef73f4ef573b17a3`。完整状态见`BUILD_STATUS.md`；本轮按用户要求结束，SD未插，未烧录/上板。

仅用于用户手动控制的MKS42C V1.1.2电机台架对照。不是HOME、机械校准或产品验收；不自动执行命令、不接管COM4、不写SD/eMMC/QSPI。保留旧scope镜像。

硬件基础：已上板scope工程，GPIO源码`df17b4e`、BSP源码`db5f75c`。从已有scope工程复制实际PS/IP/约束；复制后的运动与DMA源码逐文件与冻结Git内容比较，包括原生成头展开，不使用工作区未提交RTL。没有HP1、RS485、安全/HOME新模块、网络HMI或后台运动。原GP80400000、DMA80500000、motion80600000及SPI82..85不变。MOT2及Linux设备DMA API不变。

参数：100MHz；STEP高3125拍、低最小3125拍；DIR/EN原500拍guards；MAX_STEP_HZ=16000；A0..A2、M4禁用；原raw64/plan8/START32、EN高有效。复位及禁用STEP=0；END/STOP保留EN，shutdown显式DISABLE。首步guard=max(Q+S,E,L)+2=3127拍。软件同步以guard3127、最小槽间隔6250拍预检。3125拍是31.25µs；仅连续16kHz时50%占空比，低频不会自动保持50%。有限点还须容纳首步guard，不能直接以N/时长=16kHz构造边界点。

J12：A0 STEP/DIR/EN=3/4/5，A1=6/7/8，A2=9/10/11；GND=2，1为电源。LVCMOS33、原8mA/SLOW输出、原20ns异步GPIO预算；这不构成驱动器输入同步时序签核。驱动器HOLD模式忽略EN高低，因此软件DISABLE不能当作驱动器真实失能或硬件急停。台架应具备独立切电，机械连接/负载由用户掌控。不要带电改线，也不要让两个脉冲源并联驱动同一输入。

参考Golden仍使用200整步/转、16细分及4.5软件换算比。实际驱动细分、传动比和机械行程未确认；本版不更改Golden，不能将参考XYZ等同实物标定坐标。若驱动确为16细分，16kHz对应电机300rpm；该值不是加速度/负载能力承诺。

## 构建

从工作区根执行（工作目录必须新建，旧尝试不得覆盖）：

```powershell
python bsp/motor_test/prepare.py
python bsp/motor_test/test_rtl.py
python bsp/motor_test/test_dma.py real_dma_attempt2
python bsp/motor_test/build_hardware.py
python bsp/scripts/regenerate_motion_ps.py --work-dir motor3125_soc_prj --export-hpf
python bsp/motor_test/review.py
python bsp/motor_test/stage_vm.py
python bsp/motor_test/remote.py stage
python bsp/motor_test/remote.py status
python bsp/motor_test/remote.py package
python bsp/motor_test/remote.py status
python bsp/motor_test/remote.py download
```

PL完整综合/布局/布线实际16线程，内部100MHz，参考speed2。bitgen仅在routed setup/hold非负、覆盖/时钟/输出检查及critical诊断通过后执行。HPF、FSBL、DTB及rootfs由匹配工程重新生成。VM为uisrc@192.168.43.135，密码只在内存输入。首次ARM缺少原生成头文件的失败已保留，后补充原规范头和内核类型适配；不是绕过身份检查。SD文件打包器采用0a4ca51版本的最终交付物白名单修正，日志不得计算哈希，最终镜像/模块/直接源码按最小范围记录。

## 用户手动运行

先完成本镜像身份、启动资源和空闲状态核对。不会自动装载或使能运动。按需手动：

```sh
cat /etc/motor3125-profile
sha256sum -c /etc/delta-scope/files.sha256
modprobe bsp_gp
modprobe anlogic-dma-engine
modprobe bsp_motion
delta-scope serve --motor-bench-test > /tmp/motor3125-server.log 2>&1 &
delta-scope snapshot
```

必须看到`MOTOR3125_PROFILE H=3125 L=3125 MAX_HZ=16000`、三轴配置、STEP0/EN0、无DMA所有权及quarantine。旧`--no-motor-test`启动参数不用于此候选，避免混淆版本。init是维护REBASE并显式ENABLE，不是电机回零；不要对未知机械位置随意初始化。后续move依据保留的实际STEP位置，不反复init掩盖位置差异。

上述MOTOR3125提示是软件标识。旧MOT1寄存器ABI保持兼容，GP的PROFILE不能单独区分旧5µs和新31.25µs参数；必须使用配套BOOT/HPF并保存冷启动身份，同时先在断开驱动器时实测STEP高电平31.25µs，不能只凭rootfs文件或该提示认定PL已更新。

原示波器向量`init --xyz 0 0 -140`、去程`move --xyz 5 0 -140 --duration-ms 500`及返回`move --xyz 0 0 -140 --duration-ms 500`对应单程1/124/123步，A0只有一步。这些仍是参考数值，不新增大范围电机运行指令；实体负载及运动范围未核验时先断开机械负载。move返回成功只证明PL执行，需在驱动器STP/GND处测31.25µs及接收脉冲计数/实际转动。首步由3127拍guard开始，原5µs波形oracle不能原样使用。

本版自检：连续内核bench验证282µs点、281µs拒绝及四个STOP相位；真实保护IP的DMA/GP bench使用相同1/124/123步数但将点时长缩为10ms，检查CRC/接收/预缓存/显式START、精确duration、往返和在途STOP。原始仿真波形及边沿表在`bsp/evidence/motor3125-20261021/real_dma_attempt2/`；该目录上层的`predicted-500ms-edges.csv`是500ms逻辑预测，不是500ms实测或本次完整500ms仿真记录。新镜像的ARM实际运行和实体电机结果需上板后另行登记。

```sh
delta-scope stop
delta-scope snapshot
delta-scope shutdown
rmmod bsp_motion
```

STOP失败/quarantine须保留buffer与模块，不强卸载或自动续跑。正常shutdown应报告pulse-safe、DISABLE、RELEASE；HOLD下仍需单独确认电机供电和驱动状态。全部SD写入、用户冷启动、GPIO脉宽/电机运行及停止实测，在完成前均标为NOT_EXECUTED。
