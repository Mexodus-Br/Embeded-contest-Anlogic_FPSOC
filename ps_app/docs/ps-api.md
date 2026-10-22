> 本文保留 D1 来件描述。本目录整改增补及生产待定项见 [INTEGRATION.md](INTEGRATION.md)、[BACKEND.md](BACKEND.md) 和 [WIFI_ACCESS.md](WIFI_ACCESS.md)。

# D1 主机 API v1

2026-10-22，用户已确认 D1。以下是实现后的精确字段补充；范围仍为 localhost 主机模拟。机器 schema：[ps-api.schema.json](ps-api.schema.json)，生成/一致性检查：`python tools/ps_schema.py [--check]`。每个端点按下表选取 `$defs`，不要把整个文件当成单一请求类型。HTTP 集成测试逐个校验实际成功/失败响应。

## 类型和身份

HTTP 根为 `/api/v1`。JSON 文档版本为 1；短操作结果继承路径版本，不重复携带 schema_version。逻辑 ID 为 1～128 位 ASCII 字母、数字、`_`、`-`；随机身份是十六进制字符串。所有 **64 位** 整数均为规范十进制字符串，服务再次检查有符号/无符号范围；禁止前导零、`-0`、`+`、小数及 JSON 数值替代。32 位地址/查询、样本个数和索引可用 JSON 整数。

XYZ 为世界坐标 mm，显示角度为 °，Golden 内部 rad；绝对步数固定 `[high, low, rot, M4]`，M4 必须为 `"0"`。NaN/Infinity 不合法。参数范围、几何约束、时限及相互绑定由 C++ 校验，schema 不替代数值算法。

## 端点映射

所有端点除健康检查、静态文件和登录外都需要认证；写操作均校验 Origin 和 CSRF。

|方法/路径|请求 `$defs`|成功响应 `$defs`|
|---|---|---|
|POST `/auth`|auth_request|auth|
|GET `/auth`|无|auth|
|DELETE `/auth`|empty|logout|
|GET `/state`|无|state|
|POST `/control`|control_request|control|
|POST `/mode`|mode|mode|
|POST `/preview`|preview_request|preview|
|POST `/preview/cancel`|empty|cancel|
|POST `/commands`|run_request|command|
|GET `/commands/{id}`|无|command|
|POST `/stop`|empty|stop|
|POST `/jog/start`|jog_start|jog_started|
|POST `/jog/refresh`|jog_refresh|jog_refreshed|
|POST `/jog/end`|jog_refresh|stop|
|GET `/parameters`、`/tasks`|无|ids|
|GET `/parameters/{id}`|无|parameters|
|PUT `/parameters/{id}`|parameters|saved|
|GET `/tasks/{id}`|无|task|
|PUT `/tasks/{id}`|task|saved|
|POST `/teach`|empty|teach|
|GET `/telemetry`|无|telemetry|
|POST `/simulation/telemetry`|empty|replayed|
|POST `/simulation/inject`|inject|applied；log_burst 为 log_stats|
|POST `/logs/snapshots`|filter|snapshot|
|GET `/logs?snapshot=ID&limit=50&cursor=ID:offset`|URL 查询|page|
|GET `/logs/{event_id}`|无|event|
|GET `/logs/export?snapshot=ID`|仅 snapshot|UTF-8 JSONL：snapshot + event 逐行|
|GET `/events`|可选 Last-Event-ID|SSE，见下文|

`/api/health` 返回 `{app:"ps-simulation",version:1,simulation:true}`。PUT 参数在校验及原子保存成功后选用该版本；GET 仅读取。要选用已有版本，GET 后把相同文档 PUT 回原 ID。内置 `host_demo_v1` 同样不可变。任务保存自动补齐版本、重复方式和当前参数版本；不会执行。推荐新客户端显式携带这些字段。

## 从预览到运行

```json
{
  "schema_version": 1,
  "parameter_version": "host_demo_v1",
  "start_position_id": "从state读取",
  "task": {
    "schema_version": 1,
    "id": "task_1",
    "parameter_version": "host_demo_v1",
    "points": [{"xyz_mm": [5, 0, -140], "dwell_us": "0"}],
    "repeat": {"mode": "finite", "count": "1"}
  }
}
```

未知起点仍可返回目标逆解，但 `executable:false`、`errors` 含 POSITION_UNKNOWN、sample_count=0，没有路径/时长。有效预览绑定控制会话、参数版本、起点 ID、state_version 和 stop_epoch，30 秒过期。编辑时调用 `/preview/cancel`；客户端串行等待取消结束再发新预览，防止旧取消晚到。

运行请求为 `{boot_id,client_command_id,preview_id,deadline_monotonic_us}`。deadline 必须大于当前 PS 单调时钟且不超过它之后 2 秒。命令 ID 在 boot 内保留，重复相同请求查询原状态，改变内容拒绝 ID_CONFLICT；结构合法但执行条件被拒绝的请求同样保留失败结果。1024 个身份满后明确拒绝，不逐出旧身份。启动期限仅用于接收阶段，不中断已运行任务。

状态阶段为 received → validated → submitted → running → completed/cancelled/failed；很短的中间阶段由命令结果与日志表达。`/stop` 先返回 received 和新的 stop_epoch；GET state 随即报告 stopping，直到执行器确认模拟停止。停止失败进入 fault 且位置无效。此模拟器的 pulse_safe 标识只表示模拟停止结果，不是实机引脚证据。

`position.parameter_version` 是当前位置所属计算快照；正在运行时改参数不会改变任务。若当前选用版本不同，位置显示 unknown，重新选回匹配版本或建立模拟参考后才可用。重启不恢复上次坐标，也不重放命令；恢复记录只表示结果 unknown。

手动 start 另绑定 stop_epoch 和 2 秒启动期限，refresh_seq 从 `"0"` 起严格递增；旧刷新不续租。超时 350 ms 请求停止。撤销/过期控制会话使手动停止；已接受的自主任务继续。新方向必须等旧方向停止。

## SSE 与遥测

`event: state` 的 data 是 state（没有会话特有 you_control）；`event: log` 的 data 是 event，ID=`boot_id:event_id`。断线后按 Last-Event-ID 补发有限保留历史，每批最多 100。boot 不符、过保留期、丢弃变化或游标超前，发送 `event: gap`；客户端重新 GET state，绝不重放命令。状态约 100 ms 更新。

遥测 history 保留本次冻结回放 17 帧，latest 以 `地址:查询` 分组。last_result 是最近结果，last_valid 是同代际最近有效值，失败不补零。以最后帧的 collector/transport generation 和 revision 为当前代际，其他代际条目保持 stale；回放超过 500 ms 也 stale。原始包内时间不冒充主机时间。0x33 是命令脉冲，0x30 是 carry/value；xyz_feedback 固定 null。

## 日志边界

快照固定 boot、lower/upper_event_id、筛选条件及选中内容，后来的新记录/轮转不混入。空结果 lower_event_id=null。游标绑定 snapshot ID；快照最多 4 个，60 秒过期，10000 条/16 MiB，单页 1～100。JSONL 首行元数据可直接比对页面快照，之后每行一个完整事件；中文、多行和引号使用标准 JSON 转义，无日志哈希。

内存队列 1024、历史 10000、单条 8192 B、磁盘 4×4 MiB 轮转。入队与历史查询使用独立锁；入队使用 try_lock，满或短时争用会增加 dropped。快照把尚未写出的队列数据也纳入受限复制，元数据不把这些记录称为已落盘。gaps/dropped/retired/write_errors 明示缺失，last_flushed_event_id 仅表示流 flush，不能推导每条都写成功或掉电可靠。

并发导出上限 2，SSE 上限 4，总连接上限 32，socket 读写超时 5 秒，请求体 2 MiB、头 16 KiB。下载只接受 snapshot 逻辑 ID，不能下载任意路径。取消下载只关闭该连接，不影响任务或 STOP。墙钟不可信时只支持 clock=monotonic，要求墙钟返回 CLOCK_INVALID。

## 错误

失败统一 `{ok:false,error:{code,message,field,leg,sample,details}}`，不可用的定位字段为 null。AUTH 为 HTTP 401、NOT_FOUND 为 404、RESOURCE_LIMIT 为 429；BUSY/PREVIEW_STALE/ID_CONFLICT/CONTROL_BUSY/VERSION_CONFLICT 为 409，其余业务错误为 400。客户端依据 code，不依赖英文 message。

|类别|主要 code|处理|
|---|---|---|
|格式/版本|FORMAT、VERSION、CONFIG_RANGE|修正输入，保留原文件|
|权限/状态|AUTH、CONTROL_REQUIRED、CONTROL_BUSY、MODE、BUSY|重新核对会话或等待停止|
|时效/身份|BOOT_MISMATCH、EXPIRED、PREVIEW_STALE、STALE_INPUT、ID_CONFLICT、UNKNOWN_ID|重新读状态并由用户重新发起，禁止自动重放|
|坐标/路径|POSITION_UNKNOWN、START_MISMATCH、IK_UNREACHABLE、STEP_RANGE、WORKSPACE_RANGE、JOINT_RANGE、PATH_FORBIDDEN、PATH_DISCONTINUITY、SAMPLING_LIMIT|修正路径/参考，不执行部分结果|
|时间/脉冲|DURATION_INSUFFICIENT、PULSE_RATE|显式修改请求；不会自动拉长|
|文件/资源|VERSION_CONFLICT、STORAGE、RESOURCE_LIMIT|换版本或修复存储，不覆盖运行快照|
|遥测/日志|TELEMETRY_FORMAT、CLOCK_INVALID、SNAPSHOT_LIMIT、SNAPSHOT_EXPIRED、LOG_RETIRED|保留无效/缺失提示，重新查询不静默替换快照|

错误样本、请求构造和完整往返见 `tests/ps_service.py`；冻结字节与 64 位极值见 `tests/ps_core.py`。这两份为本机验收代码，不进入未来设备部署目录。
