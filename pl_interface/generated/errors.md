<!-- Generated from schema.json SHA256 261fa09b715dc2f636d5fa3a5f6a34f6e392e7bf04e65901576f34dcaeeb3822; GP profiles explicitly confirmed; other layouts/semantics DRAFT. -->
# Error candidate table

| Code | Name | Severity | State impact | Report |
| --- | --- | --- | --- | --- |
| 0x0000 | OK | INFO | none | ACK |
| 0x0101 | BAD_RECORD | ERROR | invalidate session / STOP | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0102 | STALE_SESSION | WARN | discard old | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0103 | SEQUENCE | ERROR | invalidate session / STOP | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0104 | TARGET_RANGE | ERROR | invalidate session / STOP | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0201 | UNEXECUTABLE | ERROR | STOP | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0202 | UNDERRUN | ERROR | STOP | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0203 | ARITHMETIC | ERROR | STOP | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0204 | POSITION_INVALID | ERROR | reject START | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0301 | LIMIT | ERROR | STOP / latch | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0302 | INTERLOCK | ERROR | STOP / latch | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0303 | ESTOP | ERROR | STOP / position invalid | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0304 | WATCHDOG | ERROR | STOP / latch | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0401 | CHECKSUM | POLICY | TBD per node | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0402 | POLL_TIMEOUT | POLICY | TBD per node | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0403 | DRIVER_ALARM | POLICY | TBD whole-machine policy | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0404 | STALE_FEEDBACK | POLICY | TBD age policy | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0501 | DMA | ERROR | STOP / invalidate session | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0502 | LINK_RESET | ERROR | invalidate session | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0503 | TELEMETRY_DROP | WARN | count / IRQ; critical policy TBD | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0601 | BAD_COMMAND | ERROR | reject transaction | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0602 | BUSY | ERROR | reject transaction | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0603 | DUP_COMMAND | ERROR | reject transaction | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0604 | BAD_CONFIG | ERROR | retain active config | ACK or GP latch + IRQ + best-effort telemetry |
| 0x0605 | FAULT_ACTIVE | ERROR | reject clear | ACK or GP latch + IRQ + best-effort telemetry |
