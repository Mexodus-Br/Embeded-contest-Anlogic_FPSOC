"""Clone accepted GP PS inputs; original board-tested project stays intact."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'work/gp_soc_prj';dst=ROOT/'work/dma_soc_prj'
if dst.exists():
    raise SystemExit('DMA project already exists; inspect rather than overwrite')
dst.mkdir()
for name in ['system','uisrc']:
    shutil.copytree(src/name,dst/name)
(dst/'system.al').write_text((src/'system.al').read_text(encoding='utf-8').replace(src.as_posix(),dst.as_posix()),encoding='utf-8')
print('Prepared',dst,'; regenerate actual GP0/HP0/IRQ/reset PS ports next')
