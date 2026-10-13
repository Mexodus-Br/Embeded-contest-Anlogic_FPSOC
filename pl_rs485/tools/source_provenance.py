"""Read-only document identities; no firmware or board operations."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT.parents[1]/'docs'
mks=DOCS/'MKS-SERVO42C'
board=DOCS/'Analogic/hardware_MLK_F3P_CZ02_DR1_20250526'
paths=[ROOT.parent/'AGENT.md',ROOT.parent/'PHASE0_CONSTRAINTS.md',ROOT.parent/'HARDWARE.md',
 mks/'README.md',mks/'Firmware/firmware.txt',mks/'User Manual/MKS SERVO42C User Manual V1.1.2.pdf',
 board/'01_硬件手册/MLK_F3P_CZ02_DR1开发板硬件使用手册.pdf',
 board/'02_原理图/MLK_F3P_DR1_250526.pdf',
 board/'08_框图及pinlist/MLK-F3P/PL-RS485管脚定义表.xlsx',
 board/'06_芯片手册/11_RS485/SP3485EN-L-TR.pdf']
data={'documents':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in paths],
 'release_note':{'url':'https://github.com/makerbase-mks/MKS-SERVO42C/releases/tag/MKS-SERVO42C-V1.1','tag':'MKS-SERVO42C-V1.1','commit_prefix':'58f9933','checked_date':'2026-10-13','summary':'release claims checksum added; serial F3 reenable may return to old position; mentions 36 absent in local 5.1 read table'},
 'actual_driver_firmware':'UNKNOWN: no board/binary interrogation performed',
 'electrical':'board PDF p14 visually checked; pin table A3:C5 XML checked; manual p21 confirms BANK33 and L17/N16/N15; SP3485 p1-2 specifies 3.3V half duplex'}
(ROOT/'evidence/sources.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('PASS document provenance')
