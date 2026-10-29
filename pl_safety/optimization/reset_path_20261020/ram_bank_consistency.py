"""Verify all actual inferred banks share tested mode, address and enable nets."""
import argparse,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--netlist',required=True);a=p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    text=Path(a.netlist).read_text();marker='  // control/core/fabric/dma_core/motion/motion/kernel/raw_fifo/ramread'
    blocks=[text[i:text.index('));',i)+3] for i in (m.start() for m in re.finditer(re.escape(marker),text))]
    result={'passed':False,'hashes_computed':False,'source':a.netlist,'banks':[]}
    try:
        assert len(blocks)==11,len(blocks)
        common=None;controls=None;used=[]
        for block in blocks:
            param_text=block[block.index('#(')+2:block.index('))\n    \\')+1]
            params={k:v for k,v in re.findall(r'\.([A-Z0-9_]+)\(([^()]*)\)',param_text) if not k.startswith('INIT')}
            for k,v in [('DATA_WIDTH_A','"40"'),('DATA_WIDTH_B','"40"'),('REGMODE_A','"NOREG"'),('REGMODE_B','"NOREG"'),('RSTAMUX','"0"'),('RSTBMUX','"0"'),('WRITEMODE_A','"NORMAL"'),('WRITEMODE_B','"NORMAL"')]:assert params[k]==v,(k,params[k])
            if common is None:common=params
            assert params==common,'A bank differs from the tested configuration'
            ports=dict(re.findall(r'\.([a-z_]+)\(([^()]*)\)',block[len(param_text):]))
            address={k:ports[k] for k in ['addra','addrb','clka','clkb']}
            # CSA/B low two input pins are individually named unconnected pins;
            # their fixed 1 values come from CSA0/1 and CSB0/1 attributes.
            for key in ['csa','csb']:address[key]=ports[key].split(',')[0]
            if controls is None:controls=address
            assert address==controls,'Address/clock/enable mismatch'
            assert "2'b00" in ports['addra'] and '/raw_fifo/wr ' in ports['addra']
            assert "2'b00" in ports['addrb'] and '/raw_fifo/rd ' in ports['addrb']
            bits=[]
            for key in ['doa','doa_extra','dob','dob_extra']:
                # The final 21-bit bank omits unused physical output ports.
                # The aggregate 0..420 exact-once check still requires every
                # logical payload bit. TD names capture outputs after their
                # consumers: metadata[100:0], duration[63:0], target[255:0].
                for field,msb,lsb in re.findall(r'/planner/(plan_data|duration_saved|target_saved) \[(\d+)(?::(\d+))?\]',ports.get(key,'')):
                    bits.extend(field+'['+str(b)+']' for b in range(int(lsb or msb),int(msb)+1))
            used.extend(bits)
            result['banks'].append({'instance':block.splitlines()[0].strip()[3:],'used_bits':sorted(bits),'configuration_matches_first':True,'control_matches_first':True})
        expected=[field+'['+str(b)+']' for field,width in [('plan_data',101),('duration_saved',64),('target_saved',256)] for b in range(width)]
        assert sorted(used)==sorted(expected),('Missing/duplicate raw bits',len(used))
        result.update(passed=True,configuration=common,controls=controls,observable_payload_bits=421,physical_slots=65,logical_capacity=64)
        print('PASS all eleven banks: identical tested mode/control, all 421 output bits present')
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
