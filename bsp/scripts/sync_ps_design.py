"""Update block-design parameter payload from the actual regenerated PS IP."""
from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
p = root / 'work/soc_prj/system'
demo = Path(r'D:\Works\Embedded_contest\docs\Analogic\01_start\02_start_Linux\04_secondary_developmemt\demo\soc_prj\system')
base = (demo / 'Design.xml').read_text(encoding='utf-8')
ps = (p / 'ip/system_ARM_Processor_System_0/DesignTmp.xml').read_text(encoding='utf-8')
pat = r'<ipxact:configurableElementValues>.*?</ipxact:configurableElementValues>'
payload = re.search(pat, ps, re.S).group()
base, n = re.subn(pat, lambda _: payload, base, count=1, flags=re.S)
assert n == 1
base = base.replace('C:/Anlogic/TD_5.9.1_DR1_2025.1_151.508/ip/depot', 'D:/Anlogic/TD_Release_2026.1_SP2.200.067/ip/depot')
(p / 'Design.xml').write_text(base, encoding='utf-8')
print('Block design synchronized to generated PS parameters')
