#!/usr/bin/python3
"""Read-only USB topology without a udev/hwdb dependency or network identifiers."""
from pathlib import Path

root = Path('/sys/bus/usb/devices')
for dev in sorted(root.iterdir()):
    if not (dev/'idVendor').exists():
        continue
    def value(name):
        try:
            return (dev/name).read_text().strip()
        except OSError:
            return 'unknown'
    print('{} vid:pid={}:{} bus={} dev={} speed={} parent={}'.format(
        dev.name,value('idVendor'),value('idProduct'),value('busnum'),
        value('devnum'),value('speed'),dev.resolve().parent.name))
    for interface in sorted(root.glob(dev.name+':*')):
        driver = interface/'driver'
        print('  {} driver={}'.format(interface.name,driver.resolve().name if driver.exists() else 'unbound'))
