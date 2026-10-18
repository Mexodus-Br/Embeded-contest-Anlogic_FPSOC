#!/bin/sh
# Invoke only after identity, USB and manual association gates. IPv4 literals only.
set -eu
I=${WIFI_INTERFACE:-wlan0}
G=${1:?gateway IPv4 required}
P=${2:?LAN peer IPv4 required}
case "$I" in ''|*[!a-zA-Z0-9_.-]*) exit 2;; esac
case "$G:$P" in *[!0-9.:]*) echo 'IPv4 literals required'; exit 2;; esac
[ -d "/sys/class/net/$I/wireless" ] || iw dev "$I" info | grep -q 'type managed'
wpa_cli -p /run/wifi-sta/control -i "$I" status | grep -qx 'wpa_state=COMPLETED'
ip -4 addr show dev "$I"
ip -4 route show dev "$I"
for host in "$G" "$P"; do
 ip -4 route get "$host" oif "$I"
done
echo 'TEN_MINUTE_OBSERVATION_BEGIN; separately ping this wireless IPv4 from the LAN PC'
echo 'USB_KERNEL_EVENTS_BEFORE'
dmesg | grep -i -E 'usb|aic|firmware|disconnect' || :
failed=0
gateway_losses=0
peer_losses=0
association_losses=0
for n in $(seq 1 120); do
 date -u '+%Y-%m-%dT%H:%M:%SZ'
 if ! wpa_cli -p /run/wifi-sta/control -i "$I" status | grep -qx 'wpa_state=COMPLETED'; then echo 'ASSOCIATION_LOST'; association_losses=$((association_losses+1)); failed=1; fi
 ping -I "$I" -c 1 -W 1 "$G" || { gateway_losses=$((gateway_losses+1)); failed=1; }
 ping -I "$I" -c 1 -W 1 "$P" || { peer_losses=$((peer_losses+1)); failed=1; }
 sleep 5
done
echo 'TEN_MINUTE_OBSERVATION_END'
echo 'USB_KERNEL_EVENTS_AFTER (compare kernel timestamps; ring wrap requires separate capture)'
dmesg | grep -i -E 'usb|aic|firmware|disconnect' || :
echo "probe_failures_seen=$failed"
echo "gateway_sent=120 gateway_lost=$gateway_losses peer_sent=120 peer_lost=$peer_losses association_loss_samples=$association_losses"
echo 'This does not certify PC-to-board reachability, controlled reconnect, or cold boot'
exit "$failed"
