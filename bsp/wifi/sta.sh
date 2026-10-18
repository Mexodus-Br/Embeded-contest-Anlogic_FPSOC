#!/bin/sh
# BusyBox-compatible, no motion commands, no secrets in stdout/process argv.
set -eu
umask 077
[ "$(id -u)" = 0 ] || { echo 'root required'; exit 1; }
R=/run/wifi-sta
C=/etc/wifi/wpa_supplicant.conf
configured=wlan0
[ ! -f /etc/wifi/interface ] || configured=$(cat /etc/wifi/interface)
I=${WIFI_INTERFACE:-$configured}
case "$I" in ''|*[!a-zA-Z0-9_.-]*) echo 'invalid interface'; exit 2;; esac
mkdir -p "$R"
chmod 700 "$R"
cli() { wpa_cli -p "$R/control" -i "$I" "$@" 2>/dev/null; }
associated() { cli status | grep -qx 'wpa_state=COMPLETED'; }
wireless() { [ -d "/sys/class/net/$I/wireless" ] || iw dev "$I" info 2>/dev/null | grep -q 'type managed'; }
terminate() {
    file=$1; expected=$2
    if [ -f "$file" ]; then
        pid=$(cat "$file")
        case "$pid" in ''|*[!0-9]*) return;; esac
        if [ -r "/proc/$pid/cmdline" ] && tr '\000' ' ' < "/proc/$pid/cmdline" | grep -q "$expected"; then
            kill "$pid" 2>/dev/null || :
        fi
        rm -f "$file"
    fi
}
clear_link() {
    terminate "$R/dhcp.pid" udhcpc
    ip -4 route flush dev "$I" 2>/dev/null || :
    ip -4 addr flush dev "$I" 2>/dev/null || :
}
cleanup() {
    clear_link
    terminate "$R/wpa.pid" wpa_supplicant
    ip link set "$I" down 2>/dev/null || :
    rm -f "$R/worker.pid"
}
case "${1:-status}" in
    start)
        wireless || { echo 'wireless interface absent; inspect USB/driver first'; exit 1; }
        [ -f "$C" ] && [ ! -L "$C" ] && [ "$(stat -c '%u:%a' "$C")" = 0:600 ] || { echo 'run wifi-configure first (root:0600)'; exit 1; }
        if [ -f "$R/worker.pid" ] && kill -0 "$(cat "$R/worker.pid")" 2>/dev/null; then echo 'already running'; exit 0; fi
        mkdir "$R/starting" 2>/dev/null || { echo 'start/stop in progress'; exit 1; }
        "$0" worker >/dev/null 2>&1 &
        echo 'STA worker requested; query wifi-sta status'
        ;;
    worker)
        echo $$ > "$R/worker.pid"
        rmdir "$R/starting"
        trap 'cleanup; exit 0' TERM INT
        trap cleanup EXIT
        ip link set "$I" up
        wpa_supplicant -B -D nl80211 -i "$I" -c "$C" -P "$R/wpa.pid" >/dev/null 2>&1
        while :; do
            if associated; then
                if ! [ -f "$R/dhcp.pid" ] || ! kill -0 "$(cat "$R/dhcp.pid")" 2>/dev/null; then
                    udhcpc -f -n -t 5 -T 3 -i "$I" -p "$R/dhcp.pid" -s /usr/libexec/wifi-udhcpc >/dev/null 2>&1 &
                    echo $! > "$R/dhcp.pid"
                fi
            else
                clear_link
            fi
            sleep 5
        done
        ;;
    stop)
        for attempt in 1 2 3; do
            [ -d "$R/starting" ] || break
            sleep 1
        done
        [ ! -d "$R/starting" ] || { echo 'worker is still starting; retry stop'; exit 1; }
        old_pid=$(cat "$R/worker.pid" 2>/dev/null || :)
        terminate "$R/worker.pid" 'wifi-sta.*worker'
        # A POSIX shell can defer its TERM trap until sleep finishes (5 seconds).
        # Do not start a replacement whose state the old cleanup could destroy.
        for attempt in 1 2 3 4 5 6 7; do
            case "$old_pid" in ''|*[!0-9]*) break;; esac
            [ -r "/proc/$old_pid/cmdline" ] || break
            tr '\000' ' ' < "/proc/$old_pid/cmdline" | grep -q 'wifi-sta.*worker' || break
            sleep 1
        done
        if [ -r "/proc/${old_pid:-none}/cmdline" ] && tr '\000' ' ' < "/proc/$old_pid/cmdline" | grep -q 'wifi-sta.*worker'; then
            echo 'worker still stopping; do not reconnect yet'; exit 1
        fi
        cleanup
        echo 'STA stopped'
        ;;
    reconnect)
        "$0" stop
        "$0" start
        ;;
    status)
        echo "interface=$I"
        wireless || { echo 'wireless_interface=absent'; exit 1; }
        cli status | sed -n '/^wpa_state=/p;/^ip_address=/p;/^key_mgmt=/p'
        ip -4 addr show dev "$I"
        ip -4 route show dev "$I"
        ;;
    scan)
        wireless || { echo 'wireless interface absent'; exit 1; }
        ip link set "$I" up
        iw dev "$I" scan | sed 's/SSID:.*/SSID: [redacted]/'
        ;;
    autostart-on)
        associated && ip -4 addr show dev "$I" | grep -q 'inet ' || { echo 'manual association and DHCP must pass first'; exit 1; }
        printf '%s\n' "$I" > /etc/wifi/interface
        touch /etc/wifi/autostart
        echo 'Autostart enabled for the configured router; cold boot still requires acceptance'
        ;;
    autostart-off) rm -f /etc/wifi/autostart; echo 'Autostart disabled';;
    *) echo 'usage: wifi-sta start|stop|status|scan|reconnect|autostart-on|autostart-off'; exit 2;;
esac
