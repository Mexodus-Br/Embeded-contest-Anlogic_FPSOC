#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] || { echo 'root required'; exit 1; }
R=/run/wifi-http
mkdir -p "$R"
chmod 700 "$R"
case "${1:-status}" in
 start)
  [ -f /etc/wifi-http/auth.json ] || { echo 'Run wifi-http-auth on local TTY first'; exit 1; }
  mkdir "$R/starting" 2>/dev/null || { echo 'Start already pending'; exit 1; }
  if [ -f "$R/server.pid" ] && kill -0 "$(cat "$R/server.pid")" 2>/dev/null; then rmdir "$R/starting"; echo 'Already running'; exit 0; fi
  /usr/sbin/wifi-http-export || { rmdir "$R/starting"; exit 1; }
  /usr/bin/python3 /usr/lib/wifi-http/server.py >/dev/null 2>&1 &
  echo $! > "$R/server.pid"
  sleep 1
  if ! kill -0 "$(cat "$R/server.pid")" 2>/dev/null; then
   rm -f "$R/server.pid"; rmdir "$R/starting"; echo 'HTTP startup failed'; exit 1
  fi
  rmdir "$R/starting"
  echo 'HTTP requested; use wifi-http status'
  ;;
 stop)
  if [ -f "$R/server.pid" ]; then
   pid=$(cat "$R/server.pid")
   case "$pid" in ''|*[!0-9]*) exit 1;; esac
   if [ -r "/proc/$pid/cmdline" ] && tr '\000' ' ' < "/proc/$pid/cmdline" | grep -q '/usr/lib/wifi-http/server.py'; then kill "$pid"; fi
   rm -f "$R/server.pid"
  fi
  ;;
 restart) "$0" stop; sleep 1; "$0" start;;
 status)
  if [ -f "$R/server.pid" ] && kill -0 "$(cat "$R/server.pid")" 2>/dev/null; then
   echo 'HTTP process running (port 8080, wireless device only)'
   grep -E '^Uid:|^Gid:' "/proc/$(cat "$R/server.pid")/status"
  else echo 'HTTP stopped'; fi
  I=wlan0; [ ! -f /etc/wifi/interface ] || I=$(cat /etc/wifi/interface)
  ip -4 addr show dev "$I" 2>/dev/null || :
  ip -o -4 addr show dev "$I" 2>/dev/null | awk '{split($4,a,"/"); print "HTTP URL: http://" a[1] ":8080/"}'
  ;;
 autostart-on)
  [ -f "$R/server.pid" ] && kill -0 "$(cat "$R/server.pid")" 2>/dev/null || { echo 'Manual HTTP start must pass first'; exit 1; }
  touch /etc/wifi-http/autostart;;
 autostart-off) rm -f /etc/wifi-http/autostart;;
 *) echo 'wifi-http start|stop|restart|status|autostart-on|autostart-off'; exit 2;;
esac
