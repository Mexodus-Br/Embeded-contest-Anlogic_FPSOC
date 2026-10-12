import copy, json, re, shutil, struct, subprocess, sys, unittest, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import codec, generate
from execution_math import feasibility

class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=ROOT/'build'; cls.build.mkdir(exist_ok=True)
        cls.cc=shutil.which('gcc')
        if not cls.cc:raise RuntimeError('gcc required; no skipped tests')
        cls.probe=cls.build/'codec_probe.exe'
        subprocess.run([cls.cc,'-std=c11','-Wall','-Wextra','-Werror','-I'+str(ROOT),str(ROOT/'tests/codec_probe.c'),'-o',str(cls.probe)],check=True)

    def motion(self,**kw):
        v=dict(session_id=1,sequence=0,batch_id=0,flags=0,axis_mask=15,duration_tick=1000,target0=0,target1=0,target2=0,target3=0)
        v.update(kw);return v

    def test_boundaries_endian_independent_layout(self):
        targets=[-(1<<63),-1,0,(1<<63)-1]
        v=self.motion(session_id=(1<<64)-1,sequence=(1<<32)-1,batch_id=0x10203040,flags=1,duration_tick=(1<<64)-1,**{'target'+str(i):x for i,x in enumerate(targets)})
        b=codec.encode('motion',v)
        payload=struct.pack('<IHHQIIIIQqqqqI',0x31544f4d,1,80,v['session_id'],v['sequence'],v['batch_id'],1,15,v['duration_tick'],*targets,0)
        self.assertEqual(b,payload+struct.pack('<I',zlib.crc32(payload)))
        self.assertEqual(b[:8],b'MOT1\x01\x00\x50\x00')
        decoded=codec.decode('motion',b)
        for k,x in v.items():self.assertEqual(decoded[k],x)
        p=subprocess.run([str(self.probe),'motion'],input=b.hex(),text=True,capture_output=True,check=True)
        self.assertEqual(p.stdout.splitlines()[0],' '.join(map(str,targets)))
        self.assertEqual(p.stdout.splitlines()[1],b.hex())
        for x in [-(1<<63)-1,1<<63]:
            with self.assertRaises(ValueError):codec.encode('motion',self.motion(target0=x))

    def test_illegal_and_truncated_records(self):
        b=codec.encode('motion',self.motion())
        for n in range(80):
            with self.assertRaises(ValueError):codec.decode('motion',b[:n])
        with self.assertRaises(ValueError):codec.decode('motion',b+b'\0')
        for offset,val in [(0,0),(4,2),(6,79),(24,2),(28,16),(72,1)]:
            bad=bytearray(b);bad[offset]=val;struct.pack_into('<I',bad,76,zlib.crc32(bad[:76]))
            with self.assertRaises(ValueError):codec.decode('motion',bad)
        bad=bytearray(b);bad[42]^=1
        with self.assertRaises(ValueError):codec.decode('motion',bad)
        p=subprocess.run([str(self.probe),'motion'],input=bad.hex(),text=True,capture_output=True)
        self.assertEqual(p.returncode,4)
        for v in [self.motion(duration_tick=0),self.motion(session_id=0),self.motion(axis_mask=0,target0=1),self.motion(flags=2)]:
            with self.assertRaises(ValueError):codec.encode('motion',v)
        self.assertEqual(codec.decode('motion',codec.encode('motion',self.motion(axis_mask=0)))['axis_mask'],0)

    def test_telemetry_layout_and_missing_feedback(self):
        v=dict(type=2,axis=1,node=3,event_tick=(1<<64)-1,sample_tick=8,age_tick=(1<<64)-9,validity=23,command_position=-(1<<63),feedback_raw=(1<<63)-1,feedback_unit=1,pulse_total=(1<<64)-1,raw_length=3,raw=b'\x03\xff\x80'+bytes(13))
        b=codec.encode('telemetry',v)
        self.assertEqual(len(b),128);self.assertEqual(b[:8],b'TLM1\x01\x00\x80\x00')
        self.assertEqual(struct.unpack_from('<qqq',b,64),(-(1<<63),-1,(1<<63)-1))
        p=subprocess.run([str(self.probe),'telemetry'],input=b.hex(),text=True,capture_output=True,check=True)
        self.assertEqual(p.stdout.splitlines()[0],f'{-(1<<63)} {(1<<63)-1} {(1<<64)-1}')
        self.assertEqual(p.stdout.splitlines()[1],b.hex())
        missing=dict(type=4,axis=255,node=2,age_tick=(1<<64)-1)
        self.assertEqual(codec.decode('telemetry',codec.encode('telemetry',missing))['validity'],0)
        for d in [dict(missing,age_tick=0),dict(missing,validity=8),dict(missing,raw_length=17),dict(missing,axis=4),dict(missing,error_code=999),dict(missing,raw=b'a'+bytes(15))]:
            with self.assertRaises(ValueError):codec.encode('telemetry',d)
        with self.assertRaises(ValueError):codec.encode('telemetry',dict(v,age_tick=0))
        for n in range(128):
            with self.assertRaises(ValueError):codec.decode('telemetry',b[:n])

    def test_schema_conflicts(self):
        source=generate.load()
        mutations=[lambda s:s['registers'][1].update(offset=0),lambda s:s['registers'][0].update(offset=1),lambda s:s['registers'][0]['fields'].append(dict(name='X',lsb=0,width=1)),lambda s:s['errors'][1].update(value=0),lambda s:s['frames']['motion']['fields'][1].update(offset=0),lambda s:s['frames']['motion']['fields'][2].update(offset=7)]
        for m in mutations:
            s=copy.deepcopy(source);m(s)
            with self.assertRaises(ValueError):generate.validate(s)
        profile_mutations=[
            lambda p:p['supported_registers'].append('NO_SUCH_REGISTER'),
            lambda p:p['supported_registers'].append('VERSION'),
            lambda p:p['irq'].update(gic_intid=p['irq']['spi']),
            lambda p:p['irq'].update(dts_cells=[0,p['irq']['gic_intid'],4]),
            lambda p:p['clock_reset'].update(gp_hz=50_000_000),
            lambda p:p['field_restrictions']['IRQ_MASK'].append('NO_SUCH_FIELD'),
            lambda p:p['expected_values'].update(FEATURES=31),
            lambda p:p['reset_overrides'].update(SNAP_DONE_SEQ=1<<32),
            lambda p:p['axi']['byte_strobe_registers'].append('VERSION'),
        ]
        for m in profile_mutations:
            s=copy.deepcopy(source);m(s['gp_control_profiles']['gp_control_probe_v1'])
            with self.assertRaises(ValueError):generate.validate(s)

    def test_gp_profile_safety_and_generated_restrictions(self):
        s=generate.load();p=s['gp_control_profiles']['gp_control_probe_v1']
        self.assertEqual(set(p['supported_commands']),{'NOP','SNAPSHOT'})
        self.assertFalse(p['deployment']['hardware_verified'])
        self.assertEqual(p['deployment']['status'],'NOT_DEPLOYABLE')
        self.assertEqual(p['board_idle_values']['external_motor_outputs'],'not exported')
        d=generate.constants(s);pre='GP_GP_CONTROL_PROBE_V1_'
        self.assertEqual(d[pre+'IRQ_PENDING_MASK'],0x81)
        self.assertEqual(d[pre+'IRQ_MASK_MASK'],0x81)
        self.assertEqual(d[pre+'FEATURES_MASK'],7)
        self.assertEqual(d[pre+'EXPECTED_FEATURES'] & (d['REG_FEATURES_MOTION_MASK']|d['REG_FEATURES_DMA_MASK']),0)
        self.assertEqual(d[pre+'SNAP_DONE_SEQ_RESET'],0xffffffff)
        self.assertEqual(d['REG_SNAP_DONE_SEQ_RESET'],0) # global unconfirmed default remains separate

    def test_generated_c_verilog_all_constants(self):
        defs=generate.constants(generate.load())
        cp=self.build/'constants.c'
        c_source='#include <stdio.h>\n#include "generated/interface_defs.h"\nint main(void){\n'+'\n'.join(f'printf("{n} %u\\n",(unsigned)PLI_{n});' for n in defs)+'\nreturn 0;}\n'
        for path,source in [(cp,c_source)]:
            if not path.exists() or path.read_bytes()!=source.encode():path.write_bytes(source.encode())
        ce=self.build/'constants.exe'
        subprocess.run([self.cc,'-std=c11','-Wall','-Werror','-I'+str(ROOT),str(cp),'-o',str(ce)],check=True)
        c=subprocess.check_output([str(ce)],text=True).splitlines()
        expect=[f'{n} {x}' for n,x in defs.items()]
        self.assertEqual(c,expect)
        # This is definition/layout consistency, not an HDL simulation claim.
        parsed={}
        for line in (ROOT/'generated/interface_defs.vh').read_text().splitlines():
            if line.startswith('`define PLI_'):
                m=re.fullmatch(r"`define PLI_([A-Z0-9_]+) 32'h([0-9A-F]{8})",line)
                self.assertIsNotNone(m,line)
                self.assertNotIn(m[1],parsed); parsed[m[1]]=int(m[2],16)
        self.assertEqual(parsed,defs)
        for name,text in generate.outputs(generate.load()).items():self.assertEqual((ROOT/'generated'/name).read_bytes(),text.encode())

    def test_golden_numeric_examples(self):
        examples=json.loads((ROOT/'examples/golden_motion.json').read_text(encoding='utf-8'))
        golden=json.loads((ROOT.parent/'golden_model/vectors/firmware_host.json').read_text(encoding='utf-8'))
        cases={c['id']:c for c in golden['cases']}
        for item in examples['examples']:
            targets=cases[item['source_id']]['expected']['absolute_steps']
            self.assertEqual([item['motion']['target'+str(i)] for i in range(3)],targets)
            self.assertEqual(codec.decode('motion',codec.encode('motion',item['motion']))['target0'],targets[0])
        for kind in ['motion','telemetry']:
            v=json.loads((ROOT/'examples'/f'{kind}.json').read_text())
            self.assertEqual(codec.encode(kind,v).hex(),(ROOT/'examples'/f'{kind}.hex').read_text().strip())

    def test_execution_math_extreme_delta_and_timing(self):
        # Artificial timing parameters, not motor defaults.
        r=feasibility(5,-5,1,2,3,0,100_000_000)
        self.assertEqual((r['delta'],r['pulses'],r['slot_min']),(10,10,10))
        self.assertEqual(feasibility(20,0,1,2,3,0,100_000_000)['slot_min'],5)
        with self.assertRaises(ValueError):feasibility(21,0,1,2,3,0,100_000_000)
        with self.assertRaises(ValueError):feasibility(20,0,1,2,3,1,100_000_000)
        with self.assertRaises(ValueError):feasibility(2,0,1,1,1,0,1_000_000)
        with self.assertRaises(ValueError):feasibility((1<<63)-1,-(1<<63),1,1,1,0,100_000_000)
        with self.assertRaises(ValueError):feasibility(0,0,(1<<64)-1,1,1,0,1)
        with self.assertRaises(ValueError):feasibility(0,0,1,0,1,0,1)
        self.assertEqual(feasibility(-8,-8,1,1,1,0,1)['pulses'],0)

if __name__=='__main__':unittest.main(verbosity=2)
