"""Minimal explicit adaptations in the isolated candidate, never product sources."""
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
S=HERE/'frozen/software'


def replace(path, old, new):
    text=path.read_text(encoding='utf-8')
    assert text.count(old)==1,(path,old)
    path.write_bytes(text.replace(old,new).encode())


def main():
    assert not (HERE/'adaptations.json').exists(),'Refuse duplicate adaptation'
    # New binding rejects legacy R5S1. It does NOT redefine old generated constants.
    path=S/'bsp/telemetry/client/bsp_rs485.c'
    replace(path,'#include "generated/gp_defs.h"', '#include "generated/gp_defs.h"\n#include "generated/interlock_defs.h"')
    for name in ['VERSION','PROFILE','CAPS','FEATURES']:
        replace(path,'gr(m,GR('+name+'))!=RG_'+name,'gr(m,GR('+name+'))!=SI_COLLECTOR_'+name)
    replace(path,'"bsp,rs485-telemetry-v1"','"bsp,rs485-telemetry-r5s2"')
    # R5S2 cannot be used as the legacy dynamic config API. All configuration
    # occurs with RUN off; readback confirms the close and final RUN write.
    replace(path,'mutex_lock(&m->gp_lock);gen=gr(m,GR(GENERATION));',
        'mutex_lock(&m->gp_lock);gen=gr(m,GR(GENERATION));\n'
        ' if(gr(m,GR(RUN))){ret=-EBUSY;goto out;}')
    replace(path,'if(!ret)gw(m,GR(RUN),c->run);',
        'if(!ret){gw(m,GR(RUN),c->run);if(gr(m,GR(RUN))!=c->run)ret=-EACCES;}')
    # Kernel definitions are adapted from the sole generated header, no new map.
    text=(S/'pl_safety/generated/interlock_defs.h').read_text(encoding='utf-8')
    kernel=text.replace('#include <stdint.h>', '#include <linux/types.h>\n#ifndef UINT32_C\n#define UINT32_C(x) x##U\n#endif')
    generated=HERE/'safety/generated';generated.mkdir(exist_ok=True)
    (generated/'interlock_defs.h').write_bytes(kernel.encode())
    shutil.copyfile(S/'pl_safety/generated/safety_defs.h',generated/'safety_defs.h')
    (S/'bsp/telemetry/generated/interlock_defs.h').write_bytes(kernel.encode())
    # Fixed authenticated file route; HTTP requests never execute collection.
    replace(S/'bsp/wifi/http/server.py',
        "'/files/network-snapshot.txt':('exports','network-snapshot.txt','text/plain; charset=utf-8')}",
        "'/files/network-snapshot.txt':('exports','network-snapshot.txt','text/plain; charset=utf-8'),\n"
        "                  '/files/integration-snapshot.json':('exports','integration-snapshot.json','application/json')}")
    replace(S/'bsp/wifi/http/export.py',
        '<p>No motion commands, uploads, directory listing or remote collection.</p>',
        '<p><a href="/files/integration-snapshot.json">Locally collected SAF2 / DMA diagnostics</a></p>\n'
        '<p>Production HOME and mechanical motion are not approved.</p>\n'
        '<p>No motion commands, uploads, directory listing or remote collection.</p>')
    schema=json.loads((S/'pl_interface/schema.json').read_text(encoding='utf-8'))
    si=schema['interlock_profiles']['gp_safety_interlock_v2']
    saf=schema['safety_profiles']['gp_safety_home_v1']
    board=(S/'bsp/telemetry/board.dtsi').read_text(encoding='utf-8').replace('bsp,rs485-telemetry-v1','bsp,rs485-telemetry-r5s2')
    board+=f'''\n/* SAF2 diagnostic-only node; no heartbeat service or motion commands. */
&soc {{
    saf2_diag: safety@{si['base']:x} {{
        compatible = "bsp,saf2-diagnostic-v1";
        reg = <0 0x{si['base']:x} 0 0x{si['size']:x}>;
        interrupt-parent = <&gic>;
        interrupts = <0 {saf['irq_spi']} 4>;
        status = "disabled";
    }};
}};
'''
    (HERE/'board-disabled.dtsi').write_bytes(board.encode())
    (HERE/'adaptations.json').write_text(json.dumps({
        'product_sources_changed':False,'legacy_definitions_changed':False,
        'r5s2':'new compatible; exact profile/caps/features; RUN-off config and RUN readback',
        'safety':'new root-only exclusive diagnostic interface; snapshot/config/explicit timeout only',
        'http':'one fixed authenticated read-only export path',
        'dt':'new nodes disabled; validated-hp1-reset-drain absent',
        'motion':'legacy client compiled for dependency check, excluded from auto startup',
        'startup':'no owner OPEN, poll, HOME, REBASE, ENABLE, START or watchdog feed'
    },indent=2)+'\n')
    print('Adapted isolated R5S2 owner, generated definitions, HTTP route and disabled DT')


if __name__=='__main__':main()
