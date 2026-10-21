"""Prepare source-only VM overlay from accepted scope commit, not dirty RTL."""
from pathlib import Path
import io,tarfile,subprocess,re
R=Path(__file__).resolve().parents[2];D=R/'bsp/motor_test';W=R/'bsp/work/motor3125_soc_prj'
base='db5f75c'
paths=['golden_model/src','golden_model/configs','golden_model/baseline','golden_model/tests',
       'bsp/scripts','bsp/configs','bsp/gp/fsbl','bsp/gp/generated','bsp/motion/provider',
       'bsp/motion/client','bsp/motion/motion_uapi.h','bsp/motion/mot2_codec.h','bsp/motion/provider_api.h',
       'bsp/motion/motion_accept.c','bsp/motion/motion-control.dtsi','bsp/scope']
data=subprocess.check_output(['git','archive',base,*paths],cwd=R)
with tarfile.open(W/'vm-input.tar','w') as out:
    with tarfile.open(fileobj=io.BytesIO(data)) as src:
        for member in src.getmembers():
            if member.isfile():out.addfile(member,src.extractfile(member))
    for src,name in [(D/'delta_scope.cpp','bsp/scope/delta_scope.cpp'),(D/'package.sh','bsp/motor_test/package.sh')]:
        out.add(src,arcname=name)
    unit=subprocess.check_output(['git','show',base+':bsp/scope/unit_scope.cpp'],cwd=R).decode().replace('  int64_t target[4]=','  need(bench_feasible(28200,4)&&!bench_feasible(28100,4),"new H/L duration boundary");\n  need(!bench_feasible(3127,1)&&bench_feasible(9377,1)&&!bench_feasible(9376,1),"guard and exact period");\n  need(bench_feasible(50000000,2398)&&!bench_feasible(50000000,8000)&&bench_feasible(50000000,7999),"500ms rate boundary");\n  int64_t target[4]=')
    buf=unit.encode();entry=tarfile.TarInfo('bsp/scope/unit_scope.cpp');entry.size=len(buf);out.addfile(entry,io.BytesIO(buf))
    header=subprocess.check_output(['git','show',base+':pl_interface/generated/interface_defs.h'],cwd=R).decode()
    kernel='/* Frozen canonical schema; kernel type adaptation only. */\n'
    for line in header.splitlines():
        if line.startswith('#define '):
            kernel+=re.sub(r'UINT32_C\(([^)]+)\)',r'(\1U)',re.sub(r'UINT64_C\(([^)]+)\)',r'(\1ULL)',line))+'\n'
    for name,text in [('interface_defs.h',header),('dma_defs.h',kernel)]:
        buf=text.encode();entry=tarfile.TarInfo('bsp/motion/generated/'+name);entry.size=len(buf);out.addfile(entry,io.BytesIO(buf))
    # Later packaging-only correction: hash final deliverables, never logs or a directory tree.
    buf=subprocess.check_output(['git','show','0a4ca51:bsp/scripts/make_sd_image.py'],cwd=R)
    entry=tarfile.TarInfo('bsp/scripts/make_sd_image.py');entry.size=len(buf);out.addfile(entry,io.BytesIO(buf))
print(W/'vm-input.tar')
