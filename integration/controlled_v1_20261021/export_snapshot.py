#!/usr/bin/python3
"""Local explicit collection only; fixed executable, fixed export, no credentials."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    if os.geteuid()!=0:raise SystemExit('Local root required')
    data=json.loads(subprocess.check_output(['/usr/bin/saf2-diag','snapshot'],timeout=5))
    # Driver emits a fixed structure; no network IDs, bootargs or raw serial logs.
    expected={'source','version','profile','caps','features','config_valid','config_id',
              'irq_pending','irq_mask','irq_events','config_accepted','config_applied','global_id','interlock_id','global','interlock',
              'time_unit','dma_ddr_quiescence','decoded','production_home_approved'}
    assert set(data)==expected
    assert data['source']=='BOARD_SAF2_DIAGNOSTIC'
    assert len(data['global'])==64 and len(data['interlock'])==32
    dma=Path('/sys/class/misc/bsp-rs485/device/integration_state')
    if dma.exists():
        state=json.loads(dma.read_text())
        assert set(state)=={'blocked','owned','quarantine','buffer_allocated','generation','packet_id',
                           'packet_bytes','actual','dma_status','dma_done','drain_validated'}
        assert all(type(v) is int and 0<=v<=0xffffffff for v in state.values())
        data['dma_owner_observation']=state
    else:data['dma_owner_observation']={'status':'NOT_BOUND_OR_NOT_OBSERVED'}
    root=Path('/srv/wifi-http/exports')
    assert root.is_dir() and not root.is_symlink() and root.stat().st_uid==0
    fd,name=tempfile.mkstemp(prefix='.integration-',dir=str(root))
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(data,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
            os.fchmod(f.fileno(),0o644)
        os.replace(name,str(root/'integration-snapshot.json'))
        d=os.open(str(root),os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
    finally:
        if os.path.exists(name):os.unlink(name)
    print('Published stable SAF2 snapshot; DMA/DDR quiescence remains unproven')


if __name__=='__main__':main()
