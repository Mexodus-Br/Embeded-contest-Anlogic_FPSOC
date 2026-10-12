import sys,unittest,struct,zlib,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import motion_v2,generate
class MotionV2(unittest.TestCase):
 def record(self):return dict(session_id=2**64-1,sequence=0,flags=1,axis_mask=15,duration_tick=100,target0=-2**63,target1=2**63-1,target2=-1,target3=0)
 def test_independent_wire_and_fields(self):
  v=self.record();b=motion_v2.encode(v)
  payload=struct.pack('<IHHQIHHQqqqqI',0x32544f4d,2,72,v['session_id'],0,1,15,100,-2**63,2**63-1,-1,0,0)
  self.assertEqual(b,payload+struct.pack('<I',zlib.crc32(payload)))
  for k,x in v.items():self.assertEqual(motion_v2.decode(b)[k],x)
 def test_corruption_and_truncation(self):
  b=motion_v2.encode(self.record())
  for n in range(len(b)):
   with self.assertRaises(ValueError):motion_v2.decode(b[:n])
   bad=bytearray(b);bad[n]^=1
   with self.assertRaises(ValueError):motion_v2.decode(bad)
  for field,val in [('version',1),('length',80),('flags',2),('axis_mask',16),('reserved',1),('session_id',0),('duration_tick',0)]:
   bad=bytearray(b);f=next(f for f in motion_v2.FRAME['fields'] if f['name']==field)
   struct.pack_into('<'+motion_v2.FORMATS[f['type']],bad,f['offset'],val);struct.pack_into('<I',bad,68,zlib.crc32(bad[:68]))
   with self.assertRaises(ValueError):motion_v2.decode(bad)
 def test_profile_sizing_and_resources(self):
  p=motion_v2.PROFILE;e=p['validation_envelope']
  self.assertEqual(p['start_min_points'],(e['maximum_supply_gap_tick']+e['margin_tick']+e['minimum_duration_tick']-1)//e['minimum_duration_tick']+e['planning_margin_points'])
  self.assertEqual(p['max_packet_records']*p['record_bytes'],65520)
  for mutation in [lambda p:p['registers'].update(PROFILE=0),lambda p:p.update(base=0x80400000),lambda p:p.update(irq_line=1),lambda p:p.update(max_packet_records=911)]:
   s=copy.deepcopy(generate.load());mutation(s['motion_integration_profiles']['gp_motion_v1'])
   with self.assertRaises(ValueError):generate.validate(s)
if __name__=='__main__':unittest.main()
