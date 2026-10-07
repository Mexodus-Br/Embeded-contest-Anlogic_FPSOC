"""Explicit HDL compiler check. Errors remain errors; no automatic retry/skip."""
import shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import generate

def main():
    if not shutil.which('iverilog') or not shutil.which('vvp'):raise RuntimeError('iverilog/vvp required')
    build=ROOT/'build';build.mkdir(exist_ok=True)
    defs=generate.constants(generate.load())
    displays=[f'$display("{n} %0d",`PLI_{n});' for n in defs]
    blocks=['initial begin\n'+'\n'.join(displays[i:i+32])+'\nend' for i in range(0,len(displays),32)]
    source='`include "generated/interface_defs.vh"\nmodule constants;\n'+'\n'.join(blocks)+'\ninitial begin #1; $finish; end endmodule\n'
    (build/'constants.v').write_bytes(source.encode())
    p=subprocess.run(['iverilog','-g2005','-I.','-s','constants','-o','build/constants.vvp','build/constants.v'],cwd=ROOT,capture_output=True,text=True,timeout=45)
    if p.returncode:raise RuntimeError(f'HDL compiler failed {p.returncode}: {p.stdout}{p.stderr}')
    lines=subprocess.check_output(['vvp','build/constants.vvp'],cwd=ROOT,text=True).splitlines()
    values=[x for x in lines if x.split(' ',1)[0] in defs]
    if len(values)!=len(defs) or sorted(values)!=sorted(f'{n} {x}' for n,x in defs.items()):raise RuntimeError('HDL constants mismatch')
    print(f'HDL compiler/simulator checked {len(defs)} constants; no motion RTL tested')

if __name__=='__main__':main()
