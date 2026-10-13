#!/bin/sh
# Resource/profile gate and explicit server only. No ENABLE or START.
set -eu
/usr/bin/bsp-readonly-check "$1"
sha256sum -c /etc/delta-scope/files.sha256
tree=/sys/firmware/devicetree/base
hex() { od -An -tx1 "$1" | tr -d ' \n'; }
test "$(hex "$tree/soc/gp-control@80400000/reg")" = 00000000804000000000000000001000
test "$(hex "$tree/soc/gp-control@80400000/interrupts")" = 000000000000005200000004
test "$(hex "$tree/soc/dma@80500000/reg")" = 00000000805000000000000000001000
test "$(hex "$tree/soc/dma@80500000/dma-channel@0/interrupts")" = 000000000000005300000004
test "$(hex "$tree/soc/dma@80500000/dma-channel@30/interrupts")" = 000000000000005400000004
test "$(hex "$tree/soc/motion-control@80600000/reg")" = 00000000806000000000000000001000
test "$(hex "$tree/soc/motion-control@80600000/interrupts")" = 000000000000005500000004
test -e "$tree/soc/motion-control@80600000/bsp,isolated-motion-test"
test -e "$tree/soc/dma@80500000/bsp,motion-exclusive-controller"
test ! -e "$tree/soc/dma@80500000/anlogic,include-sg"
modprobe bsp_gp
gp-accept /dev/bsp-gp
# Probe fails closed on PROFILE/VERSION/CAPS/FEATURES and queue capacities.
modprobe anlogic-dma-engine
modprobe bsp_motion
test -e /dev/bsp-motion
delta-scope serve --no-motor-test > /tmp/delta-scope-server.log 2>&1 &
echo $! > /tmp/delta-scope-server.pid
sleep 1
delta-scope snapshot
cat /tmp/delta-scope-server.log
echo SCOPE_READY_WAIT_FOR_HUMAN_MEASUREMENT_START
