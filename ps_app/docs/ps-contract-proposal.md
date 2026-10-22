# PS 共用契约提案 D1

状态：**用户已于 2026-10-22 确认采用 D1，继续主机模拟联调**。这是第一版主机模拟的共同契约；生产运动限值、凭据分发、存储路径、板端权限、后端健康与 HOME/联锁不因此获批。按包 `guides/WORK_PLAN.md` 的确认门槛，现可继续跨组件联调。

## OPEN-01：唯一服务与数据边界

提议一个 C++17 用户态服务，唯一执行调度器、可替换的 `ExecutionBackend`、静态离线 HTML。后端抽象只接受经过核对的内存规划结果，并提供 `status/submit/manual_target/request_stop/poll`；硬件实现由项目方提供。本机仅 `simulation` 后端，所有状态/记录包含 `simulation:true`，不自动连接设备。

HTTP 前缀 `/api/v1`，文件和主要快照使用 `schema_version:1`；短操作继承路径版本。服务提供 `boot_id`，身份为受限 ASCII 字符串；64 位计数、时间、步数为规范十进制字符串；XYZ 为 mm、角度为 °。错误对象统一 `{code,message,field,leg,sample,details}`，缺失定位字段为 null。禁止 NaN/Infinity、未知字段、任意路径、shell 或设备地址。

|端点提案|语义|
|---|---|
|GET `/state`|完整状态、模式、当前命令/来源/有效性/新鲜性、目标、参数版本；不是运动入口|
|POST `/preview`|纯规划；生成一次性预览 ID，绑定完整目标/任务快照、参数版本、起点 ID、相关状态版本和期限|
|POST `/commands`|显式运行：重新核对绑定信息、权限、期限、互斥；相同 ID/相同内容返回原结果，内容冲突拒绝|
|GET `/commands/{id}`|查询结果；收到、validated、submitted、running、completed/cancelled/failed/unknown 分开|
|POST `/stop`|独立入口，停止当前任务和未来循环；received/stopping/pulse_safe/failed 分开；故障/恢复期间仍可请求|
|POST `/mode`|静止时显式切模式；运行中拒绝。离开手动必须先 STOP 完成|
|POST `/jog/start,refresh,end`|会话规则见 OPEN-04；end 请求 STOP|
|GET/PUT `/parameters/{id}`、`/tasks/{id}`|版本化读取/原子保存；读写永不执行；不能修改已运行快照|
|POST `/teach`|仅可靠静止位置可打点；记录来源、参数和位置版本|
|GET `/telemetry`|latest/history/stats；只读 owner 投递记录，保留原代际和配置版本|
|GET `/events`|SSE，boot ID + event sequence；断线恢复丢失则明确 `gap`，客户端重新 GET state，不重放命令|
|POST `/logs/snapshots`、GET `/logs`、`/logs/{id}`、`/logs/export`|认证的只读查询/稳定快照/详情/下载；POST 只创建查询视图，不上传文件|

示例：`POST /preview` 的请求为 `{schema_version:1,parameter_version:"p1",start_position_id:"s1",task:{points:[{xyz_mm:[5,0,-140]}],repeat:{mode:"finite",count:"1"}}}`。

成功结果包含 `{preview_id:"pv1",executable:true,parameter_version:"p1",start_position_id:"s1",state_version:"7",duration_us:"…",target:{xyz_mm:[5,0,-140],joint_deg:[…],steps:["-1089","-966","-1213","0"]},expires_monotonic_us:"…",errors:[]}`。运行请求 `{boot_id:"b1",client_command_id:"c1",preview_id:"pv1",deadline_monotonic_us:"…"}`。

未知起点结果 `executable:false,errors[0].code=POSITION_UNKNOWN`，允许保留终点 IK。修改目标或参数、起点/相关状态改变、期限到达后返回 `PREVIEW_STALE`/`EXPIRED`；同 ID 不同请求返回 `ID_CONFLICT`，并发普通运动 `BUSY`，旧 boot ID `BOOT_MISMATCH`。拒绝结果不返回半份可执行轨迹。

## OPEN-02：认证及控制权

主机提议启动时本地提供随机访问令牌，经同源登录换取 HttpOnly、SameSite=Strict 会话 cookie；写请求校验 Origin 和 CSRF。SSE/日志/下载同样认证；不在 HTTP URL 路径、查询或日志暴露凭据；本机启动器临时 fragment 载入后立即移除。不以 HTTP 代替认证。

所有认证用户可查看状态并请求 STOP；普通运动由一个显式控制会话拥有。运行中不抢占控制权；失去手动控制会话即 STOP；自主任务不因浏览器关闭而停止。会话撤销不自动交给旧浏览器。硬件部署的用户/凭据/HTTP 局域网边界待项目方配置。

## OPEN-03/04：期限、方向与互斥

主机命名 fixture `host_demo_v1`：命令启动期限 2 s、预览 30 s、方向刷新 100 ms、超时 350 ms、最多预缓存 100 ms；状态/SSE 100 ms、展示 stale 500 ms。这些不是实机运动参数或 PL watchdog。

方向会话 `{boot_id,jog_id,axis:"x|y|z",sign:-1|1,speed_mm_s,refresh_seq,stop_epoch,deadline_monotonic_us}`。同一会话只允许一轴，序号严格递增；旧序号拒绝且不续租。更换方向/轴必须结束旧会话并收到停止完成，再新建。按键释放、失焦、断线、输入超时均 STOP；重连需要重新按下。启动加速到目标速度；释放使用既有 STOP，首版不承诺平滑减速。

STOP 不等待规划/磁盘/网络锁；停止失败进入 fault/unknown，保留再次 STOP 入口，不假造停止完成。启动后不再因启动期限到达中断自主任务。

## OPEN-05：参数和任务

提议 JSON 格式版本 1。参数包含唯一版本、Golden 配置映射、规划限制配置 ID；未知版本或不完整配置拒绝。保存用同目录临时文件、flush/fsync、原子替换；失败保留旧版。生产目录与掉电持久性指标另行验收。

任务点为世界 XYZ mm，可选该直线的 duration_us 和点后 dwell_us（字符串）。首次从有效当前位置直线接近第一点，每段停稳。重复显式 `{mode:"finite",count:"1..1000"}` 或 `{mode:"until_stopped"}`；默认一次，不默默无限。重复时末点至首点的返回直线也必须预览和检查；到首点后的点序一致，不隐式返回启动位置。无限重复由服务端重复已验证循环，STOP 取消当前和未来循环。参数或点编辑产生新版本；不修改已运行快照。

## OPEN-06/07：坐标来源和规划

当前位置结构 `{source:"simulation|command|estimated|feedback|unknown",valid,stale,position_id,xyz_mm,joint_deg,steps,updated_monotonic_us}`。步数存在不等于 XYZ 有效。初次真实后端/restart 为 unknown，禁止自动用目标、零点或旧持久化值补齐。

主机仅从明确的模拟参考起点/模拟执行结果示教，界面标明仿真；真实示教须项目方可靠坐标状态或经验证 FK/标定。旧工作台 FK 暂不用于真实当前位置。

Golden 原样链接；轴顺序 high/low/rot/M4，M4 禁用。PS-06 产生内存绝对目标和相对 duration，不负责 EN、START、DMA、GP 或 REBASE。72B MOT2 适配为独立纯 codec，使用生成常量。

主机 `host_demo_v1` 规划 fixture：速度 20 mm/s、加速度 100 mm/s²、最大采样间隔 10 ms、空间采样间距不超过 0.25 mm、单次最多 200000 个采样点；可检查保守工作盒及显式禁入盒、关节范围、步频/脉冲预算。所有数值随测试文件显式传入。路径逐段检查、梯形/三角形、指定时间不足拒绝；不自动拉长。采样检查必须说明分辨率，不能宣称已证明机械碰撞安全或实机误差。

## OPEN-08：日志/遥测容量和导出

日志提议 JSONL，每行一条事件：schema_version、boot_id、event_id、monotonic_us、wall_time_valid/可空墙钟、severity、component、command_id/task_id、event、details、simulation。队列接收和落盘成功分开报告；不记录凭据，不计算日志或导出哈希。

主机 fixture：日志内存队列 1024 条、事件上限 8192 B；历史最多 10000 条；单段 4 MiB、4 段轮转；快照最多 4 个、60 s 过期、最多 10000 条/16 MiB；同时导出最多 2 个，分页最大 100 条，socket 写超时 5 s。资源限制外返回明确错误，禁止无限缓存。

查询按明确 clock（boot 单调时间或有效墙钟）、级别、组件、命令/任务筛选。创建快照时固定 boot 和事件上下界并受限复制/保留选中事件；新增不会混入，轮转不改变快照。游标绑定快照和筛选条件，跨快照或过期拒绝。导出首行元数据含范围、条件、计数、truncated/gaps/durability，后续事件逐行 JSON，可还原中文与多行内容。逻辑 ID 映射批准日志，拒绝路径遍历及任意文件。

记录丢弃、序号缺口、磁盘满、写失败、轮转保留期、快照过期、取消下载必须显式呈现；未知持久化不能显示已落盘。日志写线程和网络线程不持有执行/STOP 锁。验收注入慢下载、取消、磁盘错误、队列满并并发 STOP，记录实际延迟（主机目标 <100 ms，仅 fixture，不承诺板端实时性）。

遥测复用 C decoder，原始记录及 collector/transport generation、revision、completion_serial 原样保留。latest 保留上次有效值并单列本次失败，代际变化不继承有效标签；stale 使用显式输入时间和配置周期。query33 标为命令脉冲，query30 carry/value 保留，均不自动转换 XYZ。

## 需要的决定

用户已确认采用 D1 作为**主机模拟联调契约**。按同一文档开发六组件并记录变更；生产数值/真实后端仍保持待定。实现发现需要收紧的资源边界应在此记录，不更改冻结的 Golden/PL 格式。

## 实现澄清

精确字段、端点/机器 schema、错误和样本统一见 [ps-api.md](ps-api.md)。补充取消预览、注销会话、STOP epoch、参数选用和快照下界；任务点字段固定为 points[].xyz_mm，任务绑定 parameter_version。执行器 submit 即启动已验证任务，poll 提交结果，status 读快照。日志入队与历史查询锁分离；队列满或短时入队锁争用可丢弃并计数，不宣称无损。以上为 D1 主机实现细化，不改变硬件/限值边界。
