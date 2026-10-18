#!/bin/sh
# Only configure the requested wireless interface. Never replace global DNS.
set -eu
case "${interface:-}" in ''|*[!a-zA-Z0-9_.-]*) exit 1;; esac
[ -d "/sys/class/net/$interface/wireless" ] || iw dev "$interface" info | grep -q 'type managed'
case "${1:-}" in
 deconfig) ip -4 addr flush dev "$interface"; ip -4 route flush dev "$interface";;
 bound|renew)
  ip -4 addr flush dev "$interface"
  ip -4 route flush dev "$interface"
  : "${subnet:?DHCP server did not supply a subnet mask}"
  ip addr add "$ip/$subnet" dev "$interface"
  for gateway in ${router:-}; do
   ip route add default via "$gateway" dev "$interface" metric 600
   break
  done
  ;;
esac
