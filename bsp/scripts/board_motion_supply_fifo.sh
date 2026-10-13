#!/bin/sh
# Explicit new-session finite test, FIFO50 producer / two SCHED_OTHER loads.
set -eu
trap 'test -z "${load1:-}" || kill "$load1" "$load2" 2>/dev/null || true' EXIT
/usr/bin/bsp-readonly-check 2176bfe4-02
test "$(sha256sum /usr/bin/motion-accept | cut -d' ' -f1)" = 29c2e1646f3b9d7980b398b121e982bf77c4e7d9573ae604bdb476550319b3f6
test "$(sha256sum /lib/modules/$(uname -r)/extra/bsp_motion.ko | cut -d' ' -f1)" = ce8d2418734ec437e52a4ade6927aa697275559138c897f30b17b752002ccac1
command -v chrt
modprobe bsp_motion
yes > /dev/null & load1=$!
yes > /dev/null & load2=$!
echo BSP_MOTION_FIFO50_ISOLATION_SCHEDULING_TEST_ONLY
cat /proc/stat
result=0
chrt -f 50 sh -c 'chrt -p $$; exec /usr/bin/motion-accept supply' > /tmp/motion-fifo50-result 2>&1 || result=$?
kill "$load1" "$load2"
wait "$load1" "$load2" 2>/dev/null || true
load1=
cat /tmp/motion-fifo50-result
cat /proc/stat
if test "$result" -ne 0; then /usr/bin/motion-accept idle; fi
rmmod bsp_motion
test ! -e /dev/bsp-motion
/usr/bin/gp-accept /dev/bsp-gp
cat /proc/interrupts
sleep 1
cat /proc/interrupts
cat /proc/modules
echo BSP_MOTION_FIFO50_FINISHED_BUFFERS_RELEASED_RESULT=$result
exit "$result"
