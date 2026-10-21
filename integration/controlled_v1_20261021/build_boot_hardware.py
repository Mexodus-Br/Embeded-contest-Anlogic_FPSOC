"""Explicitly authorized OFFLINE boot candidate; no board-release qualification."""
from pathlib import Path
import subprocess, json, zipfile, argparse, re
arg=argparse.ArgumentParser();arg.add_argument('--verify-existing',action='store_true');args=arg.parse_args()
H=Path(__file__).resolve().parent
P=H/'hardware'
TD=Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067')
r=json.loads((H/'evidence/final-hardware.json').read_text())
assert r['flow_completed'] and r['no_negative_setup_hold'] and r['invalid_constraints']==0
assert r['full_functional_resource_configuration_retained']
assert args.verify_existing or not (P/'system.bit').exists(), 'Preserve existing build; inspect before rerun'
script=f'''cd {P.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db route.db
set_param flow thread 16
if {{[get_param flow thread] != 16}} {{error "Expected threads=16"}}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
bitgen -bit system.bit
puts INTEGRATION_OFFLINE_BIT_COMPLETE
exit
'''
if not args.verify_existing:
    (H/'boot_bitgen.tcl').write_text(script)
    with (P/'bitgen.log').open('w') as log:
        subprocess.run([str(TD/'bin/td_commands_prompt.exe'),(H/'boot_bitgen.tcl').as_posix()],cwd=P,stdout=log,stderr=subprocess.STDOUT,check=True)
text=(P/'bitgen.log').read_text(errors='replace')
assert 'INTEGRATION_OFFLINE_BIT_COMPLETE' in text and 'Number of Thread = 16' in text
assert (P/'system.bit').stat().st_size>0
if not args.verify_existing:
    with (P/'hpf-export.log').open('w') as log:
        subprocess.run([str(TD/'bin/hpfTool.exe'),'-batch','-prj_path',str(P),'-prj_name','system',
            '-ps_path',str(P/'system/ip/system_ARM_Processor_System_0'),'-design_path',str(P/'system'),
            '-bitstream_path',str(P/'system.bit'),'-bitstream_status','latest','-ip_catalog',str(TD/'ip/depot'),
            '-tcl',str(H/'export_boot_hpf.tcl')],cwd=P,stdout=log,stderr=subprocess.STDOUT,check=True)
with zipfile.ZipFile(P/'system.hpf') as z:
    assert z.read('HPFs/system.bit')==(P/'system.bit').read_bytes()
    def params(text):
        return dict(re.findall(r'<ipxact:configurableElementValue referenceId="([^"]+)">([^<]*)</ipxact:configurableElementValue>',text))
    actual=params((P/'system/Design.xml').read_text());exported=params(z.read('HPFs/Design.xml').decode())
    assert len(actual)>500 and actual==exported,'HPF PS configuration mismatch'
    baseline=H.parents[1]/'bsp/artifacts/scope-release-final/output/release/system.hpf'
    with zipfile.ZipFile(baseline) as old:
        def macros(data):return dict(re.findall(r'^#define\s+(\w+)\s+([^\n]*)',data.decode(),re.M))
        old_m=macros(old.read('HPFs/soc_plat.h'));new_m=macros(z.read('HPFs/soc_plat.h'))
        for key in ['HPF_EXPORT_TIME','BITSTREAM_GENERATE_TIME']:old_m.pop(key);new_m.pop(key)
        assert old_m==new_m,'Generated PS/DDR/storage header values changed'
        a=old.read('HPFs/soc_plat.c').decode().replace('\r\n','\n')
        b=z.read('HPFs/soc_plat.c').decode().replace('\r\n','\n')
        hp1='''    // Config CRG_SRST, Slave_AXI_HP1_Interface: reset release
    // register: SRST_CTRL2.nic_hp1_srst_n = 0x1
    // 0xF8801078[1:1] = 0x1
    CONFIG_REG_MASK(0xF8801078, 0x00000002, 0x00000002),

    // Config HP_WIDTH, Slave_AXI_HP1_DATA_WIDTH: 64 bit
    // register: CFG_HP_WIDTH.wmode_hp1 = 0x0
    // 0xF8800084[1:1] = 0x0
    CONFIG_REG_MASK(0xF8800084, 0x00000002, 0x00000000),

'''
        assert b.count(hp1)==1 and b.replace(hp1,'')==a,'Unexpected executable PS initialization change'
        assert old.read('HPFs/soc_plat_dts.h')==z.read('HPFs/soc_plat_dts.h')
    (H/'evidence/boot-hardware.json').write_text(json.dumps({'bit_matches_hpf':True,'ps_parameters_equal':len(actual),
        'ps_header_values_equal_to_accepted_scope_except_export_times':True,
        'ps_executable_init_diff_only_hp1_reset_release_and_64bit_width':True,
        'ddr_and_storage_executable_initialization_unchanged':True,
        'hpf_design_is_ps_component_not_top_wiring':True,'threads':16,'signoff_pass':False,
        'setup_gt_1ns_waived_for_this_offline_candidate':True,'board_deployment_authorized':False},indent=2)+'\n')
print('OFFLINE bit/HPF complete; physical release gates remain open')
