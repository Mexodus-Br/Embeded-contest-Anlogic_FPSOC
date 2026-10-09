"""Explicit HDL compiler check. Errors remain errors; no automatic retry/skip."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import generate
sys.path.insert(0,str(ROOT.parent/'pl_motion'))
from sim_tools import Simulator

def main():
    build=ROOT/'build';build.mkdir(exist_ok=True)
    defs=generate.constants(generate.load())
    displays=[f'$display("{n} %0d",`PLI_{n});' for n in defs]
    blocks=['initial begin\n'+'\n'.join(displays[i:i+32])+'\nend' for i in range(0,len(displays),32)]
    source='`include "generated/interface_defs.vh"\nmodule constants;\n'+'\n'.join(blocks)+'\ninitial begin #1; $finish; end endmodule\n'
    (build/'constants.v').write_bytes(source.encode())
    sim=Simulator(build)
    sim.compile([build/'constants.v'],'constants',build/'constants.vvp',includes=[ROOT])
    lines=sim.simulate(build/'constants.vvp').splitlines()
    values=[x for x in lines if x.split(' ',1)[0] in defs]
    if len(values)!=len(defs) or sorted(values)!=sorted(f'{n} {x}' for n,x in defs.items()):raise RuntimeError('HDL constants mismatch')
    print(f'HDL compiler/simulator checked {len(defs)} constants; no motion RTL tested')

if __name__=='__main__':main()
