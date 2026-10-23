# SAF2 受控执行扩展（离线候选）

2026-10-23。新增模块源码 `bsp_saf2_exec.c`，不修改原诊断驱动、诊断结构或 ioctl 编号。复用原诊断配置/快照实现，新增 `execution_uapi.h` 的 J 组命令；无 mmap、地址/偏移参数或任意 MMIO。CAP_SYS_RAWIO、0600、独占 fd 保持。该源码尚未在匹配的目标 Linux 内核树生成 .ko；用户态真实 Linux 分支已交叉编译，实际 ioctl 函数已由宿主寄存器模型执行。

|接口|含义与证据|
|---|---|
|原 SAF2_SNAPSHOT / CONFIG / TIMEOUT_TEST|布局、编号保留；同时保留 0x200 / 0x300 快照身份检查、accepted/applied 区分|
|SAF2_OWNER_OPEN|明确打开新 owner；已有活动 PL owner 一律 EBUSY，不读出后接管；同 fd 的过期本地身份可由新 OPEN 替换|
|SAF2_OWNER_FEED|身份必须是本 fd 打开的活动 owner；序号非零严格增加，写前烧号，回读 LAST_SEQ 与资格；无内核喂狗线程|
|SAF2_OWNER_CLOSE|显式携带身份，成功回读非活动才撤销本地身份；PL 决定空闲/失能资格|
|SAF2_STOP|绕过 mailbox/config mutex，固定 STOP 写及状态读回；返回只说明请求写出|
|SAF2_CLEAR / HOME|本 fd owner 和心跳资格；递增 txn；冻结 opcode，ARG=0；提交不等于接受/完成|
|SAF2_ACK|带 ACK_ID 前后核对的只读 mailbox 反馈；HOME 完成仍查全局安全状态/位置|

软件 close/restart 不自动 OWNER_CLOSE、不续喂、不清错、不 HOME。未明确关闭的旧 owner 由 PL 原期限处理。未知写结果不复用序号/事务。仅原诊断 TIMEOUT_TEST 保留其既有实验行为。

STOP 与 HOME/CLEAR 的固定寄存器提交用短 spinlock 临界区串行化；STOP 不等待配置/快照/mailbox mutex。STOP 锁存本轮 owner 的命令取消门，迟到 HOME/CLEAR 返回 ECANCELED；仅显式关闭旧 owner、再 OPEN 新 owner 才重新开放这些命令。此软件保守门不关闭看门狗，不妨碍旧 owner 的合法报活，也不改变冻结 PL 协议。STOP 返回后仍须新快照证明排空；临界区不提供 MMIO 最坏延迟承诺。

新 compatible 为 `bsp,saf2-execution-v1`，设备名 `/dev/bsp-saf2-exec`。未来接入应在**新的、另行审批的 DT** 中替换原 `saf2_diag` 节点 compatible，保持 0x80a00000/4KiB、SPI89/IRQ7；初始仍 disabled。禁止同时绑定诊断与执行模块。没有修改受控 DT、镜像、frozen 或 PL。不要复制执行模块去覆盖已验收诊断模块。

匹配内核开发环境中的构建方式（本轮未执行此内核构建）：

```sh
make -C "$KERNEL_SOURCE" O="$KERNEL_OUTPUT" ARCH=arm64 \
  CROSS_COMPILE="$CROSS_COMPILE" M="$PWD/bsp/safety_execution" W=1 modules
```

必须使用同一内核源码、.config、Module.symvers、工具链及内核输出目录；没有这些输入时不得声称 .ko 或 modversions 合格。回归入口为 `python bsp/safety_execution/test_driver.py`，提取本次驱动实际 ioctl/open/release 函数运行寄存器模型；Windows 模型仅把 ioctl 参数指针宽度适配为 uintptr_t，不能替代 ARM64 ABI、内核、AXI 总线或实板验证。

无电机分步验收见 [NO_MOTOR_ACCEPTANCE.md](../../ps_app/docs/NO_MOTOR_ACCEPTANCE.md)。
