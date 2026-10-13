# GP service budget

First release retains the source FIFO depth8 and whole-new-record drop rule.
GP capture does not free a slot; only CONSUME does. Metadata has matching depth,
admission and pointers. Snapshot RAM is not extra sample capacity.

Compatibility profile produces 3*(8+2+8+1+1)=60 valid records/s on healthy nodes.
The 1ms fast simulation candidate requests 3*(50+10+50+5+5)=360 records/s,
11520 payload bytes/s; retries/errors produce additional full records.
Short startup bursts are serialized by the same half-duplex engine.

At 115200 actual868 clocks/bit, smallest successful query has 3 request and
3 response bytes: 520.8us serial time. Pre/post DE total20us, earliest response
after RX mask10us. RX record publication is at the final stop-bit center,
4.34us before that last bit ends; thus 516.46+20+10+1000=1546.46us
gives about646.7 records/s. Round upward to650 records/s as a healthy
throughput bound (response delays and scheduler reduce it). The default
10ms guard gives about95 records/s. These bounds use compiler timing parameters,
not measured driver latency. Nonempty task sets can fail admission before this
wire bound; admission is a scheduling budget, not a hard real-time guarantee.

A simpler conservative service envelope for the shipped fast candidate is
1000 records/s: new logical requests have >=1ms start gap and error attempts
have >=10ms isolation, so retry records cannot exceed this envelope. Default
compatibility uses100 records/s. No GP register shortens these compiled timings.
Noise/bus-busy records and valid/error attempts all occupy the same8 slots.
This envelope is invalid if integrating different timing parameters; recompute.

Starting empty, eight slots hold <=8ms at1000/s or <=80ms at100/s; equality
is unsafe under event/service coincidence. Recommend start service <=4ms in
fast mode with at least four free slots and drain to empty each batch. At360/s,
nominal empty capacity is22.2ms, but Linux average scheduling does not provide
a worst-case guarantee. A held capture consumes one slot. Scheduler start
clusters, IRQ latency, pauses in the consumer, snapshots and retries must be
included; dropped/accepted/stat_valid and missing sequences expose loss.

The C capture+consume path uses up to21 ordered D32 transactions per record
(including generation/status checks, capture and explicit consume), plus
identify once per batch in example.c. At1000/s budget >=21000 GP ops/s or
84KB/s D32 traffic; at360/s >=7560 ops/s. If each transaction costs T microseconds,
record service cost <=21T plus software copying/persistence. T and scheduler
latency must be measured in the final BSP; theoretical100MHz bus cycles are
not Linux MMIO latency. A full atomic snapshot uses486 GP transactions in the
C helper; lower-priority statistics sampling must not starve record draining.

Tests include filling to8, ten attempted enqueues (2 dropped), frozen-head
word reads under AXI backpressure, and real115200 input exceeding the queue
without consumption. Extra stress covers simultaneous full-pop/push and
seeded burst producer versus a slow GP consumer. This establishes overflow
semantics, not a board-certified Linux service deadline. Increase depth or
add an independent future telemetry transport only under a separate contract;
never backpressure motion or UART to repair software service overruns.
