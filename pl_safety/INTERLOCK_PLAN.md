# RS485 / PS heartbeat interlock preparation

2026-10-18. Status: decision review pending; no new production RTL, ABI or
production numeric parameters have been applied. This is preparation for the
combined task, not a completion or deployment handoff.

## Baseline and ownership

- Work starts at `249f3c3`; timing implementation `eccab43`, sealed by `88af6ee`.
- The current user's modified AGENT.md, unrelated files, log/ and tool logs are
  preserved. Only explicitly selected task files may eventually be committed.
- Actual complete safety top: safety_rs485_gp_ps_top with original PS, GP0,
  HP0/HP1, protected DMA/converters, nine J12 outputs, RS485 and four safety
  inputs. Original clock is 100MHz. M4 remains disabled.
- Final reference: closure_cofactor_route5, gate -1.439/0.000ns,
  place +2.786/0.000ns, route +1.133/+0.020ns setup/hold. LUT6 28185,
  Slice 35919, Slice FF 36403 plus PAD FF 9, ERAM 58, DSP 6, IO 17,
  GCLK 1, SCLK 6; other reported clock resources zero.
- a222f0d is an isolated IP experiment. It is not a replacement product IP.
  SYN-5066 remains open. No board, BSP, storage or deployment work is authorized.

## Decisions submitted for review

No reply, elapsed time, simulator fixture or a prior recommendation freezes any
of the following. The chat contains the consolidated question and alternatives.

|ID|Decision needed before behavior implementation|
|---|---|
|D1|485 timeout unit, default, min/max and common versus per-axis threshold; counters remain independent per monitored axis|
|D2|PS normal heartbeat period, timeout default and min/max|
|D3|Owner/sequence representation and restart/handover protocol; proposal: PL-issued nonzero increasing u64 owner and nonzero increasing u64 sequence, neither wraps within an epoch|
|D4|For protection, feedback timeout and PS timeout separately: EN after drain, position_valid, clear prerequisites and mandatory HOME; interruption of HOME requires complete HOME again|
|D5|First valid heartbeat/feedback qualification, motion permission with polling off, >= versus > timeout boundary and same-edge refresh priority|
|D6|Idle gate, collector reset and config-pending/application interaction, qualification invalidation and restart timebase|
|D7|Multi-source/axis latching, first-reason tie order, first timestamp and explicit clear conditions|

Suggested time encoding is the already implemented shared system_time_us,
u64/1MHz. A <2^63 interval is a mathematical encoding constraint, not a chosen
production operating range. Existing 0x3E periods are 1s compatibility / 200ms
fast candidate; the latter is unqualified for physical use. Retry, isolation,
mixed-query scheduling, and 500ms node backoff matter to the timeout budget.

## Engineering plan independent of pending decisions

|Area|Inspected seam and required work|
|---|---|
|485 control|0x80700000 existing RUN at 0x010, LOCAL_RESET 0x01c, five period shadows 0x040..0x050, mask 0x054, submit 0x05c. Keep exactly one real RUN register. Export that state to safety. Opt-in interlock gates must validate both write acceptance and application; keep legacy semantics by default.|
|Safety control|0x80a00000 existing registers through 0x060, snapshot 0x200..0x2ff. 0x100..0x1ff and >=0x300 are available candidates, not assigned ABI. Use the existing endpoint/IRQ7 and separate independent heartbeat commit from HOME mailbox busy.|
|Versioning|Keep gp_safety_home_v1 / SAF1 values and meanings. Add explicit new profile/identity for opt-in interlocks at the same physical window; generate its definitions from pl_interface/schema.json. Do not silently add new semantics to SAF1 CAPS.|
|Feedback source|rs485_transaction emits push/push_data in EMIT; rs485_multirate.observe_push/data and rs485_gp_bridge.completed_valid/raw export that same stream independently of FIFO acceptance. Branch from this event, never from FIFO pop, cache read, DMA or IRQ service.|
|Parsing|rs485_light_parse validates node/query/version/status/length and exposes enum_known (1 or 2). Only current-generation/revision, current-round valid 0x3E may refresh its axis. Protection=1 must stop; unknown enum remains diagnostic, never healthy. Counters cannot use last_valid cache.|
|Cancellation|safety_motion_service -> motion_service private stop/inhibit/invalidate/disable -> original continuous_motion/executor. HOME home_run/reference/complete must also be inhibited on the detecting edge. Preserve original direct limit/estop/STOP paths and sole STEP/DIR/EN/position owner.|
|Idle|motion_service.safety_idle includes maintenance_ok, command_busy, held AW/W and packet_busy. Combine with HOME owner, pulse_safe, queue/transport and pending-config conditions; it does not by itself prove EN off or DDR quiet.|
|Atomicity|Capture shadow mask/threshold/identity together at accepted submit. Track accepted, applied, qualified, detected, drained and acknowledged separately. B response / IRQ W1C never stands for drain completion.|
|AXI|Existing fire=held AW && held W && !BVALID. Feed at most once on that commit edge; validate full address, alignment, WSTRB and payload. Hold R/B under backpressure. Ordinary mailbox busy may not prevent heartbeat commits, but an outstanding B can backpressure this shared endpoint; PS must complete MMIO responses and avoid long locks.|
|Software|Only the single PS execution backend owns heartbeats, shared by serial/Web. Feed after critical control-loop health checks, never by an unconditional independent thread, timer or hardware refresher. PL heartbeat does not establish all software correctness. No Linux deployment or Web service in this task.|

The raw protocol cannot distinguish arbitrarily late same-address/same-length
replies crossing the isolation window. Preserve this existing physical protocol
qualification; neither new owner IDs nor local revision tags repair it.

## Test preparation / staged acceptance

The following are test obligations, not executed results. All newly added RTL
gets self-checking tests before complete-system integration. No assert reduction,
stub replacement, old-result overwrite or concurrent Questa session.

|Stage|Required checks|
|---|---|
|485 unit|Every axis protection; individual/simultaneous expiry; continuous normal updates; no first reply; re-enable/history; wrong axis/query/address; invalid frame/status/length/enum; retry/backoff; full FIFO and telemetry backpressure; generation/config/reset; illegal busy writes; IRQ/off/recovery never clears or resumes.|
|Heartbeat unit|Healthy/missing/duplicate/backward/old-owner heartbeat; first heartbeat; restart/handover; idle/HOME/pause/motion; >= or > boundary as approved; same-edge commit/expiry; u64 wrap; torn/illegal writes; AW/W order and B/R stalls; STOP and DMA reset keep watchdog ownership/protection as specified; late feed never revives.|
|Combined stop phases|All H/L/S/Q/E/OFF phases and new STEP candidates, HOME hit/finish, END, STOP, estop/limit and simultaneous causes. Compare actual pins and positions; cancel raw/prepared/planner/session/held record/partial packet and reject late data.|
|True system|Actual protected GP converter and two DMA/controllers, HP0/HP1 concurrently, UART replies into actual collector; fill diagnostic/telemetry queues, omit PS reads, apply DMA stalls/errors/resets while detecting protection. Keep original receiver/GP/cache/telemetry/motion/Golden regression.|
|ABI|Compare all old JSON leaves and generated numeric definitions. Preserve MOT2 72B, source record 32B, telemetry 64B and all old numeric values. Check every relevant generator.|
|Full top|Use the same complete top / device / speed2 reference / original 10ns and IO constraints. Explicit flow thread 16 with get_num_thread readback for synth/place/route and DB audits. Report all resources/capacities/percent/free/delta, added state and actual FF cost, gate/place/route setup+hold, real worst path levels/cell/net, data/CE/reset/clock fanout, congestion and CDC. Final route setup >1ns, hold >=0; restore and export actual original SDC if optimization budgets used.|

## Evidence and hashing

AGENT.md 11.5 supersedes historic broad sealing instructions. The following old
entry points need a task-specific scoped replacement/adaptation before use:

- tests/regressions.py hashes generated .log files.
- verify_delivery.py recursively enumerates evidence and hashes logs.
- build_td.py enumerates all cloned inputs; the historic full-project manifest
  includes non-source auxiliary inputs. Do not run this as-is for new evidence.
- timing_20261017 sealing/identity helpers also bind archived evidence and DBs.

Keep historical manifests/logs untouched. Read/compare report bytes or values
without computing hashes. Final task hashing is an explicit minimal allowlist
of essential final deliverables and their direct source, with no logs,
intermediate DBs, recursive inventory or archive workaround. Continue checking
source/IP/constraint identity without weakening functional/timing assertions.

Preparation check (no file hashes, no compiler/license, no board access):

```powershell
python pl_safety/tests/interlock_preflight.py --output pl_safety/interlock_preflight_NEW_TAG.json
```

The output path must be new; subsequent runs require another name. This check
reports preparation only. Functional verification, new full-top timing and
release signoff remain unperformed until decisions and implementation exist.

Initial preflight failed because the text-evidence gp/ folder contains only
constraints; its failure is retained in interlock_preflight_20261018.json.
The corrected preflight compares the actual complete routed project cache,
not an assumed source copy under text evidence. No functional assertion changed.
The second attempt then correctly rejected a raw-byte comparison between
include-based RS485 source and the cached project's inline-generated headers.
That failure is retained in interlock_preflight_20261018_r2.json. The check now
requires exactly the known generated-header expansion before comparison; it
does not rewrite logic or accept arbitrary differences.
