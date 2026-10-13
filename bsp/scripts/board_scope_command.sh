#!/bin/sh
# Only run measurement commands after the user's explicit start authorization.
set -eu
case "$1" in
 init) delta-scope init --xyz 0 0 -140 ;;
 outbound) delta-scope move --xyz 5 0 -140 --duration-ms 500 ;;
 return) delta-scope move --xyz 0 0 -140 --duration-ms 500 ;;
 invalid)
  delta-scope snapshot
  if delta-scope move --xyz nan 0 -140 --duration-ms 500; then exit 1; fi
  if delta-scope move --xyz 0 0 0 --duration-ms 500; then exit 1; fi
  if delta-scope move --xyz 1e100 0 -140 --duration-ms 500; then exit 1; fi
  if delta-scope move --xyz 5 0 -140 --duration-ms 1; then exit 1; fi
  delta-scope snapshot ;;
 stop-test)
  delta-scope move --xyz 5 0 -140 --duration-ms 500 > /tmp/scope-cancelled-move.log 2>&1 &
  mover=$!
  sleep 0.1
  delta-scope stop
  if wait "$mover"; then echo UNEXPECTED_COMPLETED_BEFORE_STOP; exit 1; fi
  cat /tmp/scope-cancelled-move.log
  delta-scope snapshot ;;
 snapshot) delta-scope snapshot ;;
 release)
  delta-scope stop
  delta-scope shutdown
  sleep 1
  test ! -e /run/delta-scope.sock
  cat /tmp/delta-scope-server.log
  rmmod bsp_motion
  test ! -e /dev/bsp-motion
  cat /proc/modules
  cat /proc/interrupts
  echo SCOPE_FINAL_CLIENT_UNLOADED_BUFFER_RELEASED_NO_ACTIVE_TRANSFER ;;
 *) echo invalid scope action; exit 2 ;;
esac
