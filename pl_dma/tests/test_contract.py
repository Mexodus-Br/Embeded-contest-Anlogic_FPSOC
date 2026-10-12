import copy,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'pl_interface'))
import generate
class DmaContractTests(unittest.TestCase):
 def test_gp_abi_values_unchanged(self):
  old=json.loads(subprocess.check_output(['git','show','0eecd84:pl_interface/schema.json'],cwd=ROOT))
  a=generate.constants(old);b=generate.constants(generate.load())
  for n,v in a.items():self.assertEqual(b[n],v,n)
  self.assertEqual(old['gp_control_profiles'],generate.load()['gp_control_profiles'])
 def test_reject_overlap(self):
  s=generate.load();s['dma_loopback_profiles']['dma_loopback_v1']['address']['base']=0x80400000
  with self.assertRaises(ValueError):generate.validate(s)
 def test_reject_irq_collision(self):
  s=generate.load();s['dma_loopback_profiles']['dma_loopback_v1']['irq']['mm2s_line']=0
  with self.assertRaises(ValueError):generate.validate(s)
 def test_reject_inconsistent_length(self):
  s=generate.load();s['dma_loopback_profiles']['dma_loopback_v1']['maximum_transfer_bytes']=65536
  with self.assertRaises(ValueError):generate.validate(s)
 def test_reject_mixed_clock(self):
  s=generate.load();s['dma_loopback_profiles']['dma_loopback_v1']['parameters']['AL_M_AXI_MM2S_ACLK_FREQ_HZ']=50000000
  with self.assertRaises(ValueError):generate.validate(s)
if __name__=='__main__':unittest.main()
