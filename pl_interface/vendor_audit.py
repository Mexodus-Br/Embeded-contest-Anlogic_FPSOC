"""Read-only vendor evidence; no extraction, build or board access."""
import hashlib, json, re, tarfile
from pathlib import Path

ROOT = Path(r'D:\Works\Embedded_contest\docs\Analogic')
OUT = Path(__file__).parent / 'vendor_evidence.json'
PAT = re.compile(r'input|output|parameter|\.AL_|C_INCLUDE|C_M_AXI|C_S_AXIS|C_M_AXIS|C_ADDR|C_.*WIDTH|irq|interrupt|dma_|DMA_|HP0|GP0|clk.*out|CLK|convert|scatter|cyclic|DRE|BTT|length|burst|ioremap|ioread|iowrite|cache', re.I)
records = []
def capture(name, data):
    lines = data.decode('utf-8', errors='replace').splitlines()
    records.append(dict(path=name, sha256=hashlib.sha256(data).hexdigest(),
                        lines=[dict(line=i+1, text=s) for i,s in enumerate(lines) if PAT.search(s)]))

sdk = ROOT / '03_demo/3-2_ex_fpsoc/3_2_01_sdk_base/17_axi_DMA'
for p in [sdk/'soc_sdk/axidma_s2mm_mm2s/main.c', sdk/'soc_prj/uisrc/01_rtl/system/hdl/system.v']:
    capture(str(p.relative_to(ROOT)), p.read_bytes())
ip = sdk/'soc_prj/uisrc/01_rtl/system/ip'
for folder in ['design_0_AXI_DMA_0','design_0_AXI_Protocol_Converter_0','design_0_AXI_Matrix_1','design_0_ARM_Processor_System_0','design_0_PLL_0']:
    p=ip/folder/(folder+'.v'); capture(str(p.relative_to(ROOT)),p.read_bytes())
linux=ROOT/'03_demo/3-4_ex_soc_linux/02_ex_linux_drive_F3P_DR1M90G/Sourcecode'
for chapter in ['16.plint','17.axi_gpio']:
    for p in (linux/chapter).rglob('*'):
        if p.is_file() and ((p.suffix=='.c' and 'soc_sdk' not in str(p)) or p.name=='system.v' or (p.suffix=='.dts' and 'kernel-dts' in str(p))):
            capture(str(p.relative_to(ROOT)),p.read_bytes())
train=ROOT/'04_培训demo/01_fdma_vdma_20251010'
for folder in ['fdma_test_20251008','fdma_vdma_tpg_20251010']:
    for p in (train/folder).rglob('*'):
        if p.is_file() and '.ipName.customize' not in str(p) and (p.name in ['uiFDMA.v','system.v','system_VDMA_0.v'] or (p.name=='main.c' and 'soc_base' not in str(p))):
            capture(str(p.relative_to(ROOT)),p.read_bytes())
with tarfile.open(ROOT/'uisrc-lab-anlogicM-V4.0.1.tar.gz','r|gz') as tar:
    for member in tar:
        if member.isfile() and member.name.endswith(('drivers/dma/anlogic/axi-dma.c','drivers/dma/anlogic/axi-dma-test.c','drivers/dma/anlogic/Kconfig','drivers/dma/anlogic/Makefile')):
            capture(member.name,tar.extractfile(member).read())
OUT.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(records)} sources -> {OUT.name}')
