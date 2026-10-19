# 远程备份与恢复范围

## Git中保存什么

远程推送保存已提交的源码、接口规范、必要生成物、配置/补丁、构建与测试脚本、需求和交接文档，以及历史已纳入Git的验证证据。`.gitignore`只控制未跟踪文件，不移除既有证据，不重写历史。

本次仓库整理只提交根目录的`.gitignore`、`README.md`和本文，不提交或重置其他任务的暂存/未暂存文件，也不代为提交用户的AGENT.md修改。开发任务完成后，由原任务审核并提交其文件；暂存文件也必须形成提交，才会进入远程备份。

原先仅存在本机`.git/info/exclude`中的ZIP、artifacts及工具临时图片规则已放入根`.gitignore`，克隆后也生效。各组件原有忽略规则继续保留。

## 默认留在本地的内容

| 内容 | 典型位置 | 备份方式 |
| --- | --- | --- |
| SD镜像、启动链及模块发布包、回退产物 | `bsp/artifacts/`，尤其`scope-release-final/` | 需要恢复部署能力时，另行备份选定的一致发布目录/包；不会随Git推送。 |
| Wi-Fi候选发布包 | `bsp/wifi/artifacts/` | 另行备份需要保留的候选包，并参考专项BUILD_STATUS区分构建与实板状态。 |
| 合作方生成ZIP | `deliverables/` | 可按handoff脚本重建，或另存最终交付包。 |
| 仿真/TD工作树、缓存、日志、运行结果及实验快照 | 各模块`build/`、新`evidence/`/`reports/`运行目录、优化工作目录、`.tmp/`和`log/` | 保留原位置；本次不删除、不移动。确需交接的最终报告经审核后单独显式纳入Git。 |
| 厂商资料、SDK、工具链、内核完整输出和下载缓存 | 工作区外`D:\Works\Embedded_contest\docs`及Linux构建VM | 与源码仓库分开备份；依据BSP专项文档恢复匹配依赖。 |
| Wi-Fi等凭据、本机环境 | 板端本地配置、`.env`、用户/系统配置 | 不进入源码仓库；恢复时交互配置。 |

优化目录的手写实验脚本仍可能处于未提交状态；不要因文件位于该目录就认定已备份。默认忽略的运行目录中，如确有不可重建的源码或必须移交的证据，应先按任务梳理后再显式选择文件。不要用强制添加整个目录代替审查。

## 推送前

在PowerShell中查看状态：

```powershell
Set-Location D:\Works\Embedded_contest\dev
git status --short
git log -5 --oneline
git remote -v
```

不要直接执行`git add .`。先让各开发任务完成并提交自己的改动，或明确只备份已提交的检查点。未跟踪、被忽略以及尚未提交的文件均不会被push带走。

当前配置的远程为：
`https://github.com/Mexodus-Br/Embeded-contest-Anlogic_FPSOC.git`

最后由用户执行推送。备份所有本地分支可使用：

```powershell
git push origin --all
```

若只推送当前工作分支，使用：

```powershell
git push -u origin codex/pl-safety-home-v1
```

两种方式按目标选择，不使用`--force`或`--mirror`。若远端拒绝非快进推送，先获取并核对远端差异，再决定合并方式；本次不主动修改远端。后续若创建了需要备份的标签，再另行推送相应标签。

## 恢复

克隆仓库后，按需要检出已推送的开发分支，再阅读AGENT.md、PHASE0_CONSTRAINTS.md及相关专项文档。恢复选定的本地发布包、厂商依赖和构建VM后，再按匹配版本重建或部署。

不要把Git克隆成功当作镜像/工具链也已恢复，也不要把开发中检查点当作已验收发布。SD目标身份、串口占用、板卡状态和部署授权均须在实际操作时核对。遵守现行最小哈希范围限制，不为备份递归生成日志或中间产物哈希清单。
