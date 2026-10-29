# 除NPU外首版全功能系统镜像

2026-10-29：镜像已完成，仅离线验证，未写卡、未实板运行。

- [交付路径、版本、实现和验证范围](DELIVERY.md)
- [逐项功能验收矩阵](ACCEPTANCE.md)
- [后续实板验收步骤（本轮不执行）](OPERATIONS.md)
- [11个必要最终产物SHA256](SHA256SUMS)
- [最终清单及精确源码/配置身份](release-manifest.json)
- [完整P&R/bit/HPF核对](hardware-result.json)

最终镜像在`artifacts/release-r1/sdcard.img`，512MiB。原始100MHz约束下setup WNS +0.312ns、hold +0.020ns，threads=16。源自独立冻结完整PL工程，不混入其他任务脏RTL。启动仅观察，无模拟回退；现场HOME及网页实测标定/边界输入后按条件开放完整运动。
