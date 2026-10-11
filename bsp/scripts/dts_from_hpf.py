"""Bridge TD2026 HPF names to the older vendor Linux/U-Boot DTS names.

The generated soc_plat_dts.h has known max-frequency/CPU clock inconsistencies;
take boot-critical values from the actual FSBL header and constrain unused clients.
"""
import argparse
from pathlib import Path
import re
import zipfile

p = argparse.ArgumentParser()
p.add_argument('hpf', type=Path)
p.add_argument('out', type=Path)
a = p.parse_args()
with zipfile.ZipFile(a.hpf) as z:
    header = z.read('HPFs/soc_plat.h').decode()
    generated = z.read('HPFs/soc_plat_dts.h').decode()
def value(name):
    return re.search(r'^#define\s+' + name + r'\s+(\d+)\s*$', header, re.M).group(1)
macros = {
    'AL_PROCESSOR_CORE0_CLOCK': value('CPU_CLOCK'),
    'AL_PROCESSOR_CORE1_CLOCK': value('CPU_CLOCK'),
    'AL_UART_CLOCK': value('UART_CLOCK'),
    'AL_MMC0_PS_MAX_FREQ': value('MMC0_IO_FREQ'),
    'AL_MMC1_PS_MAX_FREQ': value('MMC1_IO_FREQ'),
    'AL_DDRC_CAPACITY': '1024',
    'AL_ETH_CLOCK': 'AL_ETH0_CLOCK',
    'AL_ETH_PHY_CLOCK': 'AL_ETH0_PHY_CLOCK',
    'AL_ETH_PTP_CLOCK': 'AL_ETH0_PTP_CLOCK',
    'AL_ETH_TX_CLOCK': 'AL_ETH0_TX_CLOCK',
    'AL_ETH_RX_CLOCK': 'AL_ETH0_RX_CLOCK',
}
text = generated + '\n/* Project compatibility: actual FSBL values take precedence. */\n'
for key, val in macros.items():
    text += '#undef ' + key + '\n#define ' + key + ' ' + val + '\n'
a.out.write_text(text)
print('DTS boot-critical macros:', macros)
