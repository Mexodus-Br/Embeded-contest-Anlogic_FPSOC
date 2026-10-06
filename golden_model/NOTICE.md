`baseline/` 内文件是从 `D:\Works\Embedded_contest\docs\Arduino_firmware` 按字节复制的只读参考快照。路径、日期和 SHA-256 见 `baseline/manifest.json`。复制文件的所有原有注释均保留；本次检查的这些文件未包含版权声明或许可头，固件目录内也未找到 LICENSE/COPYING 文件。不能据此认定原代码为公有领域，或替其授权；上游版权/许可归属仍待确认。

`src/model.cpp` 中 IK 与换算表达式提取自上述源码，并标注来源。`tests/oracle.cpp` 是本任务编写的宿主适配入口；`tests/Arduino.h` 是本任务编写的无 IO 桩，并非 Arduino 官方头文件。

原快照包含既有行尾空白及混合格式，局部 `.gitattributes` 对 `baseline/*` 禁用 Git 文本换行转换和空白错误标记，避免检出或格式检查修改可追溯基线。新模型、测试及文档使用LF并接受正常空白检查。未修改原固件，也未将整机原固件编译、链接或烧录。
