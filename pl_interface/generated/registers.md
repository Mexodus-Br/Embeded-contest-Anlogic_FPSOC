<!-- Generated from schema.json SHA256 28ae6aec8a4dfaead98314874be3afa7a2501c9485dcac215e0b99c33b736386; GP and DMA profiles explicitly confirmed; other layouts/semantics DRAFT. -->
# Register table (global Draft, confirmed GP subsets below)

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
| 0x048 | IRQ_PENDING | 32 | 0x00000000 | W1C | ACK[0:0], FAULT[1:1], MOTION_LOW[2:2], TELEMETRY[3:3], DROP[4:4], END[5:5], LINK[6:6], TEST[7:7] | bitmap | set-wins W1C |
| 0x04C | IRQ_MASK | 32 | 0x00000000 | RW | ACK[0:0], FAULT[1:1], MOTION_LOW[2:2], TELEMETRY[3:3], DROP[4:4], END[5:5], LINK[6:6], TEST[7:7] | bitmap | none |
| 0x050 | SNAP_ID | 32 | 0x00000000 | RO | VALUE[31:0] | transaction | none |
| 0x054 | SNAP_VALID | 32 | 0x00000000 | RO | VALID[0:0] | bool | none |
| 0x058 | SNAP_TIME_LO | 32 | 0x00000000 | RO | VALUE[31:0] | tick | none |
| 0x05C | SNAP_TIME_HI | 32 | 0x00000000 | RO | VALUE[31:0] | tick | none |
| 0x060 | MOTION_CAPACITY | 32 | 0x00000000 | RO | VALUE[31:0] | records implemented | none |
| 0x064 | TELEMETRY_CAPACITY | 32 | 0x00000000 | RO | VALUE[31:0] | records implemented | none |
| 0x068 | TICK_HZ | 32 | 0x000F4240 | RO | VALUE[31:0] | Hz confirmed | none |
| 0x06C | TEST_RW | 32 | 0x00000000 | RW | VALUE[31:0] | scratch | byte-strobe scratch only |
| 0x070 | FEATURES | 32 | 0x00000007 | RO | NOP[0:0], SNAPSHOT[1:1], IRQ_TEST[2:2], MOTION[3:3], DMA[4:4] | profile features | none |
| 0x074 | TEST_IRQ_LEVEL | 32 | 0x00000000 | RW | ACTIVE[0:0] | test source | persistent IRQ test source; full WSTRB |
| 0x078 | LAST_TXN_ID | 32 | 0x00000000 | RO | VALUE[31:0] | transaction ID | last consumed legal new transaction |
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
| NOP | 16 |

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

## gp_control_probe_v1

USER_CONFIRMED_IMPLEMENTATION_PENDING; confirmed 2026-10-12. NOT_DEPLOYABLE.

Only this register/field subset is frozen for this profile; unlisted global entries remain Draft.

| Offset | Approved register | Profile field restriction | Profile reset |
| --- | --- | --- | --- |
| 0x000 | VERSION | all defined fields | 0x00000001 |
| 0x004 | CAPS | all defined fields | 0x0000000F |
| 0x008 | STATE | all defined fields | 0x00000000 |
| 0x010 | CMD_STATUS | all defined fields | 0x00000000 |
| 0x014 | ACK_ID | all defined fields | 0x00000000 |
| 0x018 | ACK_ERROR | all defined fields | 0x00000000 |
| 0x044 | POSITION_VALID | all defined fields | 0x00000000 |
| 0x048 | IRQ_PENDING | ACK, TEST | 0x00000000 |
| 0x04C | IRQ_MASK | ACK, TEST | 0x00000000 |
| 0x050 | SNAP_ID | all defined fields | 0x00000000 |
| 0x054 | SNAP_VALID | all defined fields | 0x00000000 |
| 0x058 | SNAP_TIME_LO | all defined fields | 0x00000000 |
| 0x05C | SNAP_TIME_HI | all defined fields | 0x00000000 |
| 0x068 | TICK_HZ | all defined fields | 0x000F4240 |
| 0x06C | TEST_RW | all defined fields | 0x00000000 |
| 0x070 | FEATURES | NOP, SNAPSHOT, IRQ_TEST | 0x00000007 |
| 0x074 | TEST_IRQ_LEVEL | all defined fields | 0x00000000 |
| 0x078 | LAST_TXN_ID | all defined fields | 0x00000000 |
| 0x080 | SNAP_A0_POSITION_LO | all defined fields | 0x00000000 |
| 0x084 | SNAP_A0_POSITION_HI | all defined fields | 0x00000000 |
| 0x088 | SNAP_A0_PULSE_LO | all defined fields | 0x00000000 |
| 0x08C | SNAP_A0_PULSE_HI | all defined fields | 0x00000000 |
| 0x090 | SNAP_A1_POSITION_LO | all defined fields | 0x00000000 |
| 0x094 | SNAP_A1_POSITION_HI | all defined fields | 0x00000000 |
| 0x098 | SNAP_A1_PULSE_LO | all defined fields | 0x00000000 |
| 0x09C | SNAP_A1_PULSE_HI | all defined fields | 0x00000000 |
| 0x0A0 | SNAP_A2_POSITION_LO | all defined fields | 0x00000000 |
| 0x0A4 | SNAP_A2_POSITION_HI | all defined fields | 0x00000000 |
| 0x0A8 | SNAP_A2_PULSE_LO | all defined fields | 0x00000000 |
| 0x0AC | SNAP_A2_PULSE_HI | all defined fields | 0x00000000 |
| 0x0B0 | SNAP_A3_POSITION_LO | all defined fields | 0x00000000 |
| 0x0B4 | SNAP_A3_POSITION_HI | all defined fields | 0x00000000 |
| 0x0B8 | SNAP_A3_PULSE_LO | all defined fields | 0x00000000 |
| 0x0BC | SNAP_A3_PULSE_HI | all defined fields | 0x00000000 |
| 0x0C0 | SNAP_STATE | all defined fields | 0x00000000 |
| 0x0C4 | SNAP_SESSION_LO | all defined fields | 0x00000000 |
| 0x0C8 | SNAP_SESSION_HI | all defined fields | 0x00000000 |
| 0x0CC | SNAP_ACCEPTED_SEQ | all defined fields | 0xFFFFFFFF |
| 0x0D0 | SNAP_DONE_SEQ | all defined fields | 0xFFFFFFFF |
| 0x0D4 | SNAP_POSITION_VALID | all defined fields | 0x00000000 |
| 0x100 | CMD_OPCODE | all defined fields | 0x00000000 |
| 0x104 | CMD_ARG | all defined fields | 0x00000000 |
| 0x108 | TXN_ID | all defined fields | 0x00000000 |
| 0x114 | CMD_SUBMIT | all defined fields | 0x00000000 |

Supported commands: SNAPSHOT, NOP.
Supported ACK errors: OK, BAD_COMMAND.
INIT/NOT_READY only; CAPS axis slots do not authorize motion. See pl_motion/GP_CONTROL_DRAFT.md and schema profile for complete semantics.

## dma_loopback_v1

USER_CONFIRMED_PL_SIMULATION_OOC_VALIDATED_NOT_BOARD_TESTED; confirmed 2026-10-12.

Window 0x80500000/0x1000; register span 0x400; full aligned D32 writes only.
MM2S line 1/SPI83; S2MM line 2/SPI84; level-high.
Shared 100000000Hz; stream 64bit; FIFO 16 beats; transfer 1..65535 bytes.

Native vendor register behavior with the profile guard; no motion record layout is frozen.

| Offset | DMA register |
| --- | --- |
| 0x000 | MM2S_CONTROL |
| 0x004 | MM2S_STATUS |
| 0x018 | MM2S_ADDRESS |
| 0x01C | MM2S_ADDRESS_MSB |
| 0x028 | MM2S_LENGTH |
| 0x030 | S2MM_CONTROL |
| 0x034 | S2MM_STATUS |
| 0x048 | S2MM_ADDRESS |
| 0x04C | S2MM_ADDRESS_MSB |
| 0x058 | S2MM_LENGTH |

## gp_motion_v1

USER_CONFIRMED; confirmed 2026-10-13.

Independent window 0x80600000/4KiB, IRQ3/SPI85; S2MM telemetry unsupported.

| Offset | Register | Access |
| --- | --- | --- |
| 0x000 | VERSION | RO |
| 0x004 | PROFILE | RO |
| 0x008 | STATUS | RO |
| 0x00C | ERROR | RO |
| 0x010 | OPCODE | RW |
| 0x014 | ARG | RW |
| 0x018 | TXN | RW |
| 0x01C | SUBMIT | WO |
| 0x020 | ACK_ID | RO |
| 0x024 | ACK_ERROR | RO |
| 0x028 | ACK_STATUS | RO |
| 0x02C | SESSION_LO | RW |
| 0x030 | SESSION_HI | RW |
| 0x034 | MAINT | RW |
| 0x038 | STOP | WO |
| 0x03C | PACKET_ARM | WO |
| 0x040 | RECOVER_GEN | RW |
| 0x044 | SNAP_REQ | WO |
| 0x048 | SNAP_ID | RO |
| 0x04C | SNAP_VALID | RO |
| 0x050 | IRQ_PENDING | W1C |
| 0x054 | IRQ_MASK | RW |
| 0x058 | FIFO_LEVEL | RO |
| 0x05C | PLAN_LEVEL | RO |
| 0x060 | BUFFERED | RO |
| 0x064 | RAW_CAPACITY | RO |
| 0x068 | PLAN_CAPACITY | RO |
| 0x06C | START_THRESHOLD | RO |
| 0x070 | LINK_GEN | RO |
| 0x074 | LINK_READY | RO |
| 0x078 | PACKET_COUNT | RO |
| 0x07C | ACCEPT_SEQ | RO |
| 0x080 | DONE_SEQ | RO |
| 0x084 | ACTIVE_SEQ | RO |
| 0x088 | ACCEPT_VALID | RO |
| 0x08C | DONE_VALID | RO |
| 0x100 | REBASE_0 | RW |
| 0x104 | REBASE_1 | RW |
| 0x108 | REBASE_2 | RW |
| 0x10C | REBASE_3 | RW |
| 0x110 | REBASE_4 | RW |
| 0x114 | REBASE_5 | RW |
| 0x118 | REBASE_6 | RW |
| 0x11C | REBASE_7 | RW |
| 0x200 | SNAP_0 | RO |
| 0x204 | SNAP_1 | RO |
| 0x208 | SNAP_2 | RO |
| 0x20C | SNAP_3 | RO |
| 0x210 | SNAP_4 | RO |
| 0x214 | SNAP_5 | RO |
| 0x218 | SNAP_6 | RO |
| 0x21C | SNAP_7 | RO |
| 0x220 | SNAP_8 | RO |
| 0x224 | SNAP_9 | RO |
| 0x228 | SNAP_10 | RO |
| 0x22C | SNAP_11 | RO |
| 0x230 | SNAP_12 | RO |
| 0x234 | SNAP_13 | RO |
| 0x238 | SNAP_14 | RO |
| 0x23C | SNAP_15 | RO |
| 0x240 | SNAP_16 | RO |
| 0x244 | SNAP_17 | RO |
| 0x248 | SNAP_18 | RO |
| 0x24C | SNAP_19 | RO |
| 0x250 | SNAP_20 | RO |
| 0x254 | SNAP_21 | RO |
| 0x258 | SNAP_22 | RO |
| 0x25C | SNAP_23 | RO |
| 0x260 | SNAP_24 | RO |
| 0x264 | SNAP_25 | RO |
| 0x268 | SNAP_26 | RO |
| 0x26C | SNAP_27 | RO |
| 0x270 | SNAP_28 | RO |
| 0x274 | SNAP_29 | RO |
| 0x278 | SNAP_30 | RO |
| 0x27C | SNAP_31 | RO |
| 0x090 | ACTIVE_VALID | RO |
| 0x094 | ACCEPT_COUNT | RO |
| 0x098 | DONE_COUNT | RO |
| 0x09C | STALE_COUNT | RO |
| 0x0A0 | REJECT_COUNT | RO |
| 0x0A4 | CANCEL_COUNT | RO |
| 0x0A8 | STOP_COUNT | RO |
| 0x0AC | END_COUNT | RO |
| 0x0B0 | CAPS | RO |
| 0x0B4 | FEATURES | RO |
| 0x280 | SNAP_32 | RO |
| 0x284 | SNAP_33 | RO |
| 0x288 | SNAP_34 | RO |
| 0x28C | SNAP_35 | RO |
| 0x290 | SNAP_36 | RO |
| 0x294 | SNAP_37 | RO |
| 0x298 | SNAP_38 | RO |
| 0x29C | SNAP_39 | RO |
| 0x2A0 | SNAP_40 | RO |
| 0x2A4 | SNAP_41 | RO |
| 0x2A8 | SNAP_42 | RO |
| 0x2AC | SNAP_43 | RO |
| 0x2B0 | SNAP_44 | RO |
| 0x2B4 | SNAP_45 | RO |
| 0x2B8 | SNAP_46 | RO |
| 0x2BC | SNAP_47 | RO |
| 0x2C0 | SNAP_48 | RO |
| 0x2C4 | SNAP_49 | RO |
| 0x2C8 | SNAP_50 | RO |
| 0x2CC | SNAP_51 | RO |
| 0x2D0 | SNAP_52 | RO |
| 0x2D4 | SNAP_53 | RO |
| 0x2D8 | SNAP_54 | RO |
| 0x2DC | SNAP_55 | RO |
| 0x2E0 | SNAP_56 | RO |
| 0x2E4 | SNAP_57 | RO |
| 0x2E8 | SNAP_58 | RO |
| 0x2EC | SNAP_59 | RO |
| 0x2F0 | SNAP_60 | RO |
| 0x2F4 | SNAP_61 | RO |
| 0x2F8 | SNAP_62 | RO |
| 0x2FC | SNAP_63 | RO |

## gp_rs485_v1

USER_CONFIRMED; confirmed 2026-10-14.

Candidate window 0x80700000/4KiB; IRQ4/SPI86; BSP final audit required.

| Offset | Register | Access |
| --- | --- | --- |
| 0x000 | VERSION | RO |
| 0x004 | PROFILE | RO |
| 0x008 | CAPS | RO |
| 0x00C | FEATURES | RO |
| 0x010 | RUN | RW |
| 0x014 | STATUS | RO |
| 0x018 | GENERATION | RO |
| 0x01C | LOCAL_RESET | WO |
| 0x020 | IRQ_PENDING | W1C |
| 0x024 | IRQ_MASK | RW |
| 0x028 | LAST_ACCESS_ERROR | RO |
| 0x02C | FIFO_LEVEL | RO |
| 0x040 | SHADOW_PERIOD0 | RW |
| 0x044 | SHADOW_PERIOD1 | RW |
| 0x048 | SHADOW_PERIOD2 | RW |
| 0x04C | SHADOW_PERIOD3 | RW |
| 0x050 | SHADOW_PERIOD4 | RW |
| 0x054 | SHADOW_MASK | RW |
| 0x058 | TXN_ID | RW |
| 0x05C | CFG_SUBMIT | WO |
| 0x060 | CFG_STATE | RO |
| 0x064 | CFG_TXN | RO |
| 0x068 | CFG_ERROR | RO |
| 0x06C | CFG_REVISION | RO |
| 0x070 | CFG_SEQUENCE | RO |
| 0x074 | CFG_TIME_LO | RO |
| 0x078 | CFG_TIME_HI | RO |
| 0x07C | CFG_GENERATION | RO |
| 0x080 | CURRENT_PERIOD0 | RO |
| 0x084 | CURRENT_PERIOD1 | RO |
| 0x088 | CURRENT_PERIOD2 | RO |
| 0x08C | CURRENT_PERIOD3 | RO |
| 0x090 | CURRENT_PERIOD4 | RO |
| 0x094 | CURRENT_MASK | RO |
| 0x098 | CURRENT_LOAD | RO |
| 0x0A0 | CAPTURE | WO |
| 0x0A4 | CAPTURE_ID | RO |
| 0x0A8 | CAPTURE_STATUS | RO |
| 0x0AC | CAPTURE_GENERATION | RO |
| 0x0B0 | CAPTURE_REVISION | RO |
| 0x0B4 | CONSUME_ID | WO |
| 0x0B8 | ABANDON_ID | WO |
| 0x0BC | LAST_CONSUMED_ID | RO |
| 0x0C0 | WORD0 | RO |
| 0x0C4 | WORD1 | RO |
| 0x0C8 | WORD2 | RO |
| 0x0CC | WORD3 | RO |
| 0x0D0 | WORD4 | RO |
| 0x0D4 | WORD5 | RO |
| 0x0D8 | WORD6 | RO |
| 0x0DC | WORD7 | RO |
| 0x100 | SNAP_REQ_ID | RW |
| 0x104 | SNAP_SUBMIT | WO |
| 0x108 | SNAP_STATUS | RO |
| 0x10C | SNAP_ID | RO |
