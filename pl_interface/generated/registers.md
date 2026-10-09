<!-- Generated from schema.json SHA256 ca03b985fdb71ead9f236ed5c6f79d48549793d1b1f67125ec1fadd00446a9c8; DRAFT semantics. -->
# Register candidate table

| Offset | Name | Width | Reset | Access | Fields | Unit | Side effect |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0x000 | VERSION | 32 | 0x00000001 | RO | VALUE[31:0] | version | none |
| 0x004 | CAPS | 32 | 0x0000000F | RO | AXES[3:0] | axis capability bits | none |
| 0x008 | STATE | 32 | 0x00000000 | RO | ENUM[7:0] | state enum | none |
| 0x00C | CONFIG_GENERATION | 32 | 0x00000000 | RO | VALUE[31:0] | generation | none |
| 0x010 | CMD_STATUS | 32 | 0x00000000 | RO | BUSY[0:0], ACK_VALID[1:1], ACCEPTED[2:2], COMPLETED[3:3] | flags | none |
| 0x014 | ACK_ID | 32 | 0x00000000 | RO | VALUE[31:0] | transaction | none |
| 0x018 | ACK_ERROR | 32 | 0x00000000 | RO | VALUE[31:0] | error | none |
| 0x01C | SESSION_LO | 32 | 0x00000000 | RO | VALUE[31:0] | id | none |
| 0x020 | SESSION_HI | 32 | 0x00000000 | RO | VALUE[31:0] | id | none |
| 0x024 | ACCEPTED_SEQ | 32 | 0xFFFFFFFF | RO | VALUE[31:0] | sequence | none |
| 0x028 | DONE_SEQ | 32 | 0xFFFFFFFF | RO | VALUE[31:0] | sequence | none |
| 0x02C | MOTION_LEVEL | 32 | 0x00000000 | RO | VALUE[31:0] | records | none |
| 0x030 | TELEMETRY_LEVEL | 32 | 0x00000000 | RO | VALUE[31:0] | records | none |
| 0x034 | FAULT_BITS | 32 | 0x00000000 | RO | RECORD[0:0], MOTION[1:1], SAFETY[2:2], COMM[3:3], DMA[4:4], CONTROL[5:5] | bitmap | none |
| 0x038 | FAULT_FIRST_CODE | 32 | 0x00000000 | RO | VALUE[31:0] | error | none |
| 0x03C | FAULT_TIME_LO | 32 | 0x00000000 | RO | VALUE[31:0] | tick | none |
| 0x040 | FAULT_TIME_HI | 32 | 0x00000000 | RO | VALUE[31:0] | tick | none |
| 0x044 | POSITION_VALID | 32 | 0x00000000 | RO | AXES[3:0] | axis bitmap | none |
| 0x048 | IRQ_PENDING | 32 | 0x00000000 | W1C | ACK[0:0], FAULT[1:1], MOTION_LOW[2:2], TELEMETRY[3:3], DROP[4:4], END[5:5], LINK[6:6] | bitmap | set-wins W1C |
| 0x04C | IRQ_MASK | 32 | 0x00000000 | RW | ACK[0:0], FAULT[1:1], MOTION_LOW[2:2], TELEMETRY[3:3], DROP[4:4], END[5:5], LINK[6:6] | bitmap | none |
| 0x050 | SNAP_ID | 32 | 0x00000000 | RO | VALUE[31:0] | transaction | none |
| 0x054 | SNAP_VALID | 32 | 0x00000000 | RO | VALID[0:0] | bool | none |
| 0x058 | SNAP_TIME_LO | 32 | 0x00000000 | RO | VALUE[31:0] | tick | none |
| 0x05C | SNAP_TIME_HI | 32 | 0x00000000 | RO | VALUE[31:0] | tick | none |
| 0x060 | MOTION_CAPACITY | 32 | 0x00000000 | RO | VALUE[31:0] | records implemented | none |
| 0x064 | TELEMETRY_CAPACITY | 32 | 0x00000000 | RO | VALUE[31:0] | records implemented | none |
| 0x068 | TICK_HZ | 32 | 0x000F4240 | RO | VALUE[31:0] | Hz confirmed | none |
| 0x080 | SNAP_A0_POSITION_LO | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x084 | SNAP_A0_POSITION_HI | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x088 | SNAP_A0_PULSE_LO | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x08C | SNAP_A0_PULSE_HI | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x090 | SNAP_A1_POSITION_LO | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x094 | SNAP_A1_POSITION_HI | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x098 | SNAP_A1_PULSE_LO | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x09C | SNAP_A1_PULSE_HI | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x0A0 | SNAP_A2_POSITION_LO | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x0A4 | SNAP_A2_POSITION_HI | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x0A8 | SNAP_A2_PULSE_LO | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x0AC | SNAP_A2_PULSE_HI | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x0B0 | SNAP_A3_POSITION_LO | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x0B4 | SNAP_A3_POSITION_HI | 32 | 0x00000000 | RO | VALUE[31:0] | step | none |
| 0x0B8 | SNAP_A3_PULSE_LO | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x0BC | SNAP_A3_PULSE_HI | 32 | 0x00000000 | RO | VALUE[31:0] | pulse | none |
| 0x0C0 | SNAP_STATE | 32 | 0x00000000 | RO | ENUM[7:0] | state | snapshot payload |
| 0x0C4 | SNAP_SESSION_LO | 32 | 0x00000000 | RO | VALUE[31:0] | id | snapshot payload |
| 0x0C8 | SNAP_SESSION_HI | 32 | 0x00000000 | RO | VALUE[31:0] | id | snapshot payload |
| 0x0CC | SNAP_ACCEPTED_SEQ | 32 | 0x00000000 | RO | VALUE[31:0] | sequence | snapshot payload |
| 0x0D0 | SNAP_DONE_SEQ | 32 | 0x00000000 | RO | VALUE[31:0] | sequence | snapshot payload |
| 0x0D4 | SNAP_POSITION_VALID | 32 | 0x00000000 | RO | AXES[3:0] | bitmap | snapshot payload |
| 0x100 | CMD_OPCODE | 32 | 0x00000000 | RW | ENUM[7:0] | none | command shadow |
| 0x104 | CMD_ARG | 32 | 0x00000000 | RW | VALUE[31:0] | none | command shadow |
| 0x108 | TXN_ID | 32 | 0x00000000 | RW | VALUE[31:0] | none | command shadow |
| 0x10C | CMD_SESSION_LO | 32 | 0x00000000 | RW | VALUE[31:0] | none | command shadow |
| 0x110 | CMD_SESSION_HI | 32 | 0x00000000 | RW | VALUE[31:0] | none | command shadow |
| 0x114 | CMD_SUBMIT | 32 | 0x00000000 | WO | VALUE[31:0] | none | full strobe capture transaction |
| 0x118 | WD_TOKEN | 32 | 0x00000000 | WO | VALUE[31:0] | none | new token kick |
| 0x120 | REBASE_A0_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x124 | REBASE_A0_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x128 | REBASE_A1_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x12C | REBASE_A1_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x130 | REBASE_A2_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x134 | REBASE_A2_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x138 | REBASE_A3_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x13C | REBASE_A3_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | rebase shadow |
| 0x200 | CFG_AXIS_ENABLE | 32 | 0x00000000 | RW | AXES[3:0] | mask | config shadow; atomic CONFIG_COMMIT |
| 0x204 | CFG_NODE_ENABLE | 32 | 0x00000000 | RW | AXES[3:0] | mask | config shadow; atomic CONFIG_COMMIT |
| 0x208 | CFG_WD_ENABLE | 32 | 0x00000000 | RW | ENABLE[0:0] | bool | config shadow; atomic CONFIG_COMMIT |
| 0x20C | CFG_WD_TIMEOUT_LO | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow; atomic CONFIG_COMMIT |
| 0x210 | CFG_WD_TIMEOUT_HI | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow; atomic CONFIG_COMMIT |
| 0x214 | CFG_PREBUFFER | 32 | 0x00000000 | RW | VALUE[31:0] | records | config shadow; atomic CONFIG_COMMIT |
| 0x218 | CFG_DURATION_MIN_LO | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow; atomic CONFIG_COMMIT |
| 0x21C | CFG_DURATION_MIN_HI | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow; atomic CONFIG_COMMIT |
| 0x220 | CFG_DURATION_MAX_LO | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow; atomic CONFIG_COMMIT |
| 0x224 | CFG_DURATION_MAX_HI | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow; atomic CONFIG_COMMIT |
| 0x240 | CFG_A0_HIGH | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x244 | CFG_A0_LOW | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x248 | CFG_A0_DIR_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x24C | CFG_A0_DIR_HOLD | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x250 | CFG_A0_EN_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x254 | CFG_A0_MAX_RATE | 32 | 0x00000000 | RW | VALUE[31:0] | Hz | config shadow |
| 0x258 | CFG_A0_TARGET_MIN_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x25C | CFG_A0_TARGET_MIN_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x260 | CFG_A0_TARGET_MAX_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x264 | CFG_A0_TARGET_MAX_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x268 | CFG_A0_NODE_ID | 32 | 0x00000000 | RW | NODE[7:0] | address | config shadow |
| 0x26C | CFG_A0_POLARITY | 32 | 0x00000000 | RW | STEP_ACTIVE[0:0], DIR_POSITIVE[1:1], EN_ACTIVE[2:2] | STEP/DIR/EN bits | config shadow |
| 0x270 | CFG_A0_COMM_POLICY | 32 | 0x00000000 | RW | POLICY[1:0] | TBD | config shadow |
| 0x274 | CFG_A0_FAIL_THRESHOLD | 32 | 0x00000000 | RW | VALUE[31:0] | poll | config shadow |
| 0x278 | CFG_A0_FRESH_LIMIT | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow |
| 0x280 | CFG_A1_HIGH | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x284 | CFG_A1_LOW | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x288 | CFG_A1_DIR_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x28C | CFG_A1_DIR_HOLD | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x290 | CFG_A1_EN_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x294 | CFG_A1_MAX_RATE | 32 | 0x00000000 | RW | VALUE[31:0] | Hz | config shadow |
| 0x298 | CFG_A1_TARGET_MIN_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x29C | CFG_A1_TARGET_MIN_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x2A0 | CFG_A1_TARGET_MAX_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x2A4 | CFG_A1_TARGET_MAX_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x2A8 | CFG_A1_NODE_ID | 32 | 0x00000000 | RW | NODE[7:0] | address | config shadow |
| 0x2AC | CFG_A1_POLARITY | 32 | 0x00000000 | RW | STEP_ACTIVE[0:0], DIR_POSITIVE[1:1], EN_ACTIVE[2:2] | STEP/DIR/EN bits | config shadow |
| 0x2B0 | CFG_A1_COMM_POLICY | 32 | 0x00000000 | RW | POLICY[1:0] | TBD | config shadow |
| 0x2B4 | CFG_A1_FAIL_THRESHOLD | 32 | 0x00000000 | RW | VALUE[31:0] | poll | config shadow |
| 0x2B8 | CFG_A1_FRESH_LIMIT | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow |
| 0x2C0 | CFG_A2_HIGH | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x2C4 | CFG_A2_LOW | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x2C8 | CFG_A2_DIR_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x2CC | CFG_A2_DIR_HOLD | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x2D0 | CFG_A2_EN_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x2D4 | CFG_A2_MAX_RATE | 32 | 0x00000000 | RW | VALUE[31:0] | Hz | config shadow |
| 0x2D8 | CFG_A2_TARGET_MIN_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x2DC | CFG_A2_TARGET_MIN_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x2E0 | CFG_A2_TARGET_MAX_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x2E4 | CFG_A2_TARGET_MAX_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x2E8 | CFG_A2_NODE_ID | 32 | 0x00000000 | RW | NODE[7:0] | address | config shadow |
| 0x2EC | CFG_A2_POLARITY | 32 | 0x00000000 | RW | STEP_ACTIVE[0:0], DIR_POSITIVE[1:1], EN_ACTIVE[2:2] | STEP/DIR/EN bits | config shadow |
| 0x2F0 | CFG_A2_COMM_POLICY | 32 | 0x00000000 | RW | POLICY[1:0] | TBD | config shadow |
| 0x2F4 | CFG_A2_FAIL_THRESHOLD | 32 | 0x00000000 | RW | VALUE[31:0] | poll | config shadow |
| 0x2F8 | CFG_A2_FRESH_LIMIT | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow |
| 0x300 | CFG_A3_HIGH | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x304 | CFG_A3_LOW | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x308 | CFG_A3_DIR_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x30C | CFG_A3_DIR_HOLD | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x310 | CFG_A3_EN_SETUP | 32 | 0x00000000 | RW | VALUE[31:0] | cycle | config shadow |
| 0x314 | CFG_A3_MAX_RATE | 32 | 0x00000000 | RW | VALUE[31:0] | Hz | config shadow |
| 0x318 | CFG_A3_TARGET_MIN_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x31C | CFG_A3_TARGET_MIN_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x320 | CFG_A3_TARGET_MAX_LO | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x324 | CFG_A3_TARGET_MAX_HI | 32 | 0x00000000 | RW | VALUE[31:0] | step | config shadow |
| 0x328 | CFG_A3_NODE_ID | 32 | 0x00000000 | RW | NODE[7:0] | address | config shadow |
| 0x32C | CFG_A3_POLARITY | 32 | 0x00000000 | RW | STEP_ACTIVE[0:0], DIR_POSITIVE[1:1], EN_ACTIVE[2:2] | STEP/DIR/EN bits | config shadow |
| 0x330 | CFG_A3_COMM_POLICY | 32 | 0x00000000 | RW | POLICY[1:0] | TBD | config shadow |
| 0x334 | CFG_A3_FAIL_THRESHOLD | 32 | 0x00000000 | RW | VALUE[31:0] | poll | config shadow |
| 0x338 | CFG_A3_FRESH_LIMIT | 32 | 0x00000000 | RW | VALUE[31:0] | tick | config shadow |
| 0x380 | STAT_REJECTED | 32 | 0x00000000 | RO | VALUE[31:0] | saturating count | none |
| 0x384 | STAT_STALE | 32 | 0x00000000 | RO | VALUE[31:0] | saturating count | none |
| 0x388 | STAT_UNDERRUN | 32 | 0x00000000 | RO | VALUE[31:0] | saturating count | none |
| 0x38C | STAT_TELEMETRY_DROP | 32 | 0x00000000 | RO | VALUE[31:0] | saturating count | none |
| 0x390 | STAT_DMA_ERROR | 32 | 0x00000000 | RO | VALUE[31:0] | saturating count | none |
| 0x394 | STAT_COMM_FAIL | 32 | 0x00000000 | RO | VALUE[31:0] | saturating count | none |

## Commands

| Name | Value |
| --- | --- |
| CONFIG_COMMIT | 1 |
| OPEN_SESSION | 2 |
| ENABLE | 3 |
| START | 4 |
| STOP | 5 |
| PAUSE | 6 |
| RESUME | 7 |
| DISABLE | 8 |
| CLEAR_FAULT | 9 |
| FLUSH | 10 |
| REBASE | 11 |
| HOME | 12 |
| SNAPSHOT | 13 |
| CLEAR_STATS | 14 |
| LINK_RECOVER | 15 |

## States

| Name | Value |
| --- | --- |
| INIT | 0 |
| NOT_READY | 1 |
| READY | 2 |
| RUNNING | 3 |
| PAUSING | 4 |
| PAUSED | 5 |
| STOPPING | 6 |
| FAULT | 7 |
| HOMING | 8 |
