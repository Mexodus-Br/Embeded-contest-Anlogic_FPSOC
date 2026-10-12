"""BSP driver-reviewed candidate; hardware and board validation are separate."""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
profile=json.loads((ROOT/'pl_interface/schema.json').read_text())['dma_loopback_profiles']['dma_loopback_v1']
generated=(ROOT/'pl_interface/generated/interface_defs.h').read_text()
schema_sha=hashlib.sha256((ROOT/'pl_interface/schema.json').read_bytes()).hexdigest()
assert schema_sha in generated.splitlines()[0]
directory=ROOT/'bsp/dma/generated';directory.mkdir(exist_ok=True)
lines=[re.sub(r'UINT32_C\(([^)]+)\)',r'(\1U)',line) for line in generated.splitlines() if line.startswith('#define PLI_DMA_')]
(directory/'dma_defs.h').write_text('/* Derived from unique schema generator; do not edit. */\n'+'\n'.join(lines)+'\n')
(directory/'inputs.json').write_text(json.dumps({'profile':'dma_loopback_v1','schema_sha256':schema_sha,'shared_header_sha256':hashlib.sha256((ROOT/'pl_interface/generated/interface_defs.h').read_bytes()).hexdigest(),'pl_source_commit':'7de13f1c5260c8ffad255eb43a28342e7eb32e06'},indent=2)+'\n')
text=(ROOT/'pl_dma/configs/dma-candidate.dtsi').read_text()
assert 'anlogic,include-sg;' not in text
text=text.replace('        status = "disabled";','        bsp,loopback-pair;\n        status = "disabled";',1)
text+='''
/ {
    bsp_dma_loop_client: dma-loopback-test {
        compatible = "bsp,dma-loopback-test-v1";
        dmas = <&pl_dma_loop 0>, <&pl_dma_loop 1>;
        dma-names = "tx", "rx";
        status = "disabled";
    };
};
'''
(ROOT/'bsp/dma/dma-control.dtsi').write_text(text)
print('Prepared disabled DMA/provider/client candidate; actual driver ignores clock names; hardware H16 100MHz remains required')
