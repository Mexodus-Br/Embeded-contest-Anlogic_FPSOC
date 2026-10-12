"""Deterministic definitions from the sole schema. Python stdlib only."""
import argparse, hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'schema.json'
SIZES = {'u8':1, 'u16':2, 'u32':4, 'u64':8, 'i64':8, 'bytes16':16}

def load():
    s=json.loads(SOURCE.read_text(encoding='utf-8'))
    validate(s)
    return s

def validate(s):
    names=set(); addresses=set()
    def unique(n):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',n) or n in names:
            raise ValueError('invalid/duplicate name: '+n)
        names.add(n)
    for r in s['registers']:
        unique('REG_'+r['name']); a=r['offset']
        if a%4 or not 0<=a<4096 or a in addresses or r['width']!=32:raise ValueError('register overlap/alignment')
        if r['access'] not in ('RO','RW','WO','W1C') or not 0<=r['reset']<2**32:raise ValueError('register properties')
        addresses.add(a); bits=0; fn=set()
        for f in r['fields']:
            if f['name'] in fn or f['lsb']<0 or f['width']<=0 or f['lsb']+f['width']>32:raise ValueError('field range/name')
            fn.add(f['name']); m=((1<<f['width'])-1)<<f['lsb']
            if bits&m:raise ValueError('bit overlap')
            bits|=m
    codes=set()
    for e in s['errors']:
        unique('ERR_'+e['name'])
        if e['value'] in codes or not 0<=e['value']<2**32:raise ValueError('duplicate/range error code')
        codes.add(e['value'])
    if len(set(s['commands'].values()))!=len(s['commands']):raise ValueError('duplicate opcode')
    regs={r['name']:r for r in s['registers']}
    errors={e['name'] for e in s['errors']}
    for name,p in s.get('gp_control_profiles',{}).items():
        unique('GP_'+name.upper())
        a=p['address']; irq=p['irq']; clk=p['clock_reset']
        if (a['base']%a['size'] or a['size']!=4096 or
            a['base']<0 or a['base']+a['size']>2**a['address_width'] or
            a['data_width']!=32):raise ValueError('GP window/width')
        if irq['gic_intid']!=irq['spi']+32 or irq['dts_cells']!=[0,irq['spi'],4] or irq['trigger']!='level-high':raise ValueError('GP IRQ mapping/trigger')
        if clk['gp_hz']!=clk['control_hz'] or clk['control_hz']%clk['timestamp_hz']:raise ValueError('GP shared clock/timestamp')
        supported=p['supported_registers']
        if len(set(supported))!=len(supported) or any(n not in regs for n in supported):raise ValueError('GP register subset')
        if any(n not in s['commands'] for n in p['supported_commands']) or any(n not in errors for n in p['supported_errors']) or any(n not in s['states'] for n in p['supported_states']):raise ValueError('GP command/error/state subset')
        for n,fields in p['field_restrictions'].items():
            available={f['name'] for f in regs[n]['fields']} if n in regs else set()
            if n not in supported or len(set(fields))!=len(fields) or not set(fields)<=available:raise ValueError('GP field subset')
        for n,val in p['reset_overrides'].items():
            if n not in supported or not 0<=val<2**32:raise ValueError('GP reset override')
        for n,val in p['expected_values'].items():
            if n not in supported or regs[n]['reset']!=val:raise ValueError('GP identity/reset mismatch')
        for key,accesses in [('byte_strobe_registers',('RW',)),('full_strobe_registers',('RW','WO','W1C'))]:
            for n in p['axi'][key]:
                if n not in supported or regs[n]['access'] not in accesses:raise ValueError('GP strobe/access mismatch')
        if set(p['axi']['byte_strobe_registers'])&set(p['axi']['full_strobe_registers']):raise ValueError('GP strobe overlap')
    for name,p in s.get('dma_loopback_profiles',{}).items():
        a=p['address']; q=p['parameters']; irq=p['irq']
        if a['base']%4096 or a['size']!=4096 or a['register_span']!=1024 or a['address_width']!=33 or a['data_width']!=32:raise ValueError('DMA window')
        for g in s.get('gp_control_profiles',{}).values():
            b=g['address']
            if max(a['base'],b['base'])<min(a['base']+a['size'],b['base']+b['size']):raise ValueError('DMA/GP overlap')
            if g['irq']['pl_line'] in [irq['mm2s_line'],irq['s2mm_line']]:raise ValueError('DMA/GP IRQ collision')
        if irq['mm2s_line']==irq['s2mm_line'] or irq['mm2s_intid']!=irq['mm2s_spi']+32 or irq['s2mm_intid']!=irq['s2mm_spi']+32:raise ValueError('DMA IRQ mapping')
        if q['AL_INCLUDE_SG'] or q['AL_MICRO_DMA'] or q['AL_PRMRY_IS_ACLK_ASYNC'] or q['AL_SG_INCLUDE_STSCNTRL_STRM']:raise ValueError('DMA simple synchronous profile')
        if p['maximum_transfer_bytes']!=(1<<q['AL_SG_LENGTH_WIDTH'])-1 or p['fifo_depth']<2:raise ValueError('DMA length/FIFO')
        if any(q[k]!=p['clock_hz'] for k in q if k.endswith('FREQ_HZ')):raise ValueError('DMA frequency')
    for n,f in s['frames'].items():
        occupied=set(); fieldnames=set()
        for x in f['fields']:
            if x['name'] in fieldnames:raise ValueError('duplicate frame field')
            fieldnames.add(x['name']); size=SIZES[x['type']]
            occupied_new=set(range(x['offset'],x['offset']+size))
            if occupied&occupied_new or min(occupied_new)<0 or max(occupied_new)>=f['length']:raise ValueError('frame overlap/range')
            occupied |= occupied_new
        if occupied!=set(range(f['length'])) or f['fields'][-1]['name']!='crc' or f['fields'][-1]['offset']!=f['length']-4:raise ValueError('frame gap/crc')
    for p in s.get('motion_integration_profiles',{}).values():
        if p['base']%4096 or p['size']!=4096 or p['irq_intid']!=p['irq_spi']+32:raise ValueError('motion resource')
        offsets=list(p['registers'].values())
        if len(set(offsets))!=len(offsets) or any(x%4 or not 0<=x<4096 for x in offsets):raise ValueError('motion register overlap')
        if p['record_bytes']!=s['frames']['motion_stream_v2']['length'] or p['max_packet_records']*p['record_bytes']>65535:raise ValueError('motion packet length')
        if p['raw_depth']<2 or p['plan_depth']<2 or not 1<=p['start_min_points']<=p['raw_depth']+p['plan_depth']+1:raise ValueError('motion capacity')
        for q in s.get('gp_control_profiles',{}).values():
            a=q['address']
            if max(p['base'],a['base'])<min(p['base']+4096,a['base']+a['size']) or p['irq_line']==q['irq']['pl_line']:raise ValueError('motion GP overlap')
        for q in s.get('dma_loopback_profiles',{}).values():
            a=q['address']
            if max(p['base'],a['base'])<min(p['base']+4096,a['base']+a['size']) or p['irq_line'] in (q['irq']['mm2s_line'],q['irq']['s2mm_line']):raise ValueError('motion DMA overlap')

def constants(s):
    out={'ABI_VERSION':s['version']}
    for r in s['registers']:
        pre='REG_'+r['name']; out[pre]=r['offset']; out[pre+'_RESET']=r['reset']
        for f in r['fields']:
            out[pre+'_'+f['name']+'_SHIFT']=f['lsb']
            out[pre+'_'+f['name']+'_MASK']=((1<<f['width'])-1)<<f['lsb']
    out.update({'ERR_'+e['name']:e['value'] for e in s['errors']})
    out.update({'CMD_'+n:v for n,v in s['commands'].items()})
    out.update({'STATE_'+n:v for n,v in s.get('states',{}).items()})
    for name,p in s.get('gp_control_profiles',{}).items():
        pre='GP_'+name.upper()
        out[pre+'_ABI_VERSION']=p['abi_version']
        for key in ['base','size','address_width','data_width','id_width']:
            out[pre+'_'+key.upper()]=p['address'][key]
        for key in ['pl_line','gic_intid','spi']:
            out[pre+'_IRQ_'+key.upper()]=p['irq'][key]
        for key in ['gp_hz','control_hz','timestamp_hz']:
            out[pre+'_'+key.upper()]=p['clock_reset'][key]
        for n,val in p['expected_values'].items():out[pre+'_EXPECTED_'+n]=val
        for n,val in p['reset_overrides'].items():out[pre+'_'+n+'_RESET']=val
        regs={r['name']:r for r in s['registers']}
        for n,fields in p['field_restrictions'].items():
            out[pre+'_'+n+'_MASK']=sum(((1<<f['width'])-1)<<f['lsb'] for f in regs[n]['fields'] if f['name'] in fields)
    for name,p in s.get('dma_loopback_profiles',{}).items():
        pre='DMA_'+name.upper()
        for key,value in p['address'].items():
            if isinstance(value,int) and not isinstance(value,bool):out[pre+'_'+key.upper()]=value
        for key,value in p['irq'].items():
            if isinstance(value,int) and not isinstance(value,bool):out[pre+'_IRQ_'+key.upper()]=value
        for key in ['clock_hz','memory_address_width','hp_address_width','hp_id_width','stream_width','fifo_depth','maximum_transfer_bytes','minimum_transfer_bytes','address_alignment_bytes']:
            out[pre+'_'+key.upper()]=p[key]
        for key,value in p['parameters'].items():out[pre+'_'+key]=value
        for key,value in p.get('control_registers',{}).items():out[pre+'_REG_'+key]=value
    for name,p in s.get('motion_integration_profiles',{}).items():
        pre='MOTION_'+name.upper()
        for key,value in p.items():
            if isinstance(value,int) and not isinstance(value,bool):out[pre+'_'+key.upper()]=value
        for key in ['registers','snapshot_words']:
            for n,value in p[key].items():out[pre+'_'+('REG_' if key=='registers' else 'SNAP_WORD_')+n]=value
        for key in ['status_bits','irq_bits','ack_bits','feature_bits']:
            for n,value in p[key].items():out[pre+'_'+key.upper()+'_'+n+'_MASK']=1<<value
        for group,fields in p['snapshot_fields'].items():
            for n,(shift,width) in fields.items():
                out[pre+'_SNAP_'+group+'_'+n+'_SHIFT']=shift
                out[pre+'_SNAP_'+group+'_'+n+'_MASK']=((1<<width)-1)<<shift
    for n,f in s['frames'].items():
        pre=n.upper(); out[pre+'_LENGTH']=f['length']
        for x in f['fields']:
            out[pre+'_'+x['name'].upper()+'_OFFSET']=x['offset']
            out[pre+'_'+x['name'].upper()+'_SIZE']=SIZES[x['type']]
            if 'constant' in x:out[pre+'_'+x['name'].upper()+'_VALUE']=x['constant']
            for bit,number in x.get('bits',{}).items():out[pre+'_'+x['name'].upper()+'_'+bit+'_MASK']=1<<number
            for label,number in x.get('labels',{}).items():out[pre+'_'+x['name'].upper()+'_'+label]=number
    return out

def outputs(s):
    digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    banner='Generated from schema.json SHA256 '+digest+'; GP and DMA profiles explicitly confirmed; other layouts/semantics DRAFT.'
    c=['/* '+banner+' */','#ifndef PL_INTERFACE_DEFS_H','#define PL_INTERFACE_DEFS_H','#include <stdint.h>']
    v=['// '+banner,'`ifndef PL_INTERFACE_DEFS_VH','`define PL_INTERFACE_DEFS_VH']
    for n,val in constants(s).items():
        c.append(f'#define PLI_{n} UINT32_C(0x{val:08X})')
        v.append(f'`define PLI_{n} 32\'h{val:08X}')
    c.extend(['#endif','']); v.extend(['`endif',''])
    table=['<!-- '+banner+' -->','# Register table (global Draft, confirmed GP subsets below)','', '| Offset | Name | Width | Reset | Access | Fields | Unit | Side effect |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in s['registers']:
        fields=', '.join(f"{x['name']}[{x['lsb']+x['width']-1}:{x['lsb']}]" for x in r['fields'])
        table.append(f"| 0x{r['offset']:03X} | {r['name']} | 32 | 0x{r['reset']:08X} | {r['access']} | {fields} | {r['unit']} | {r['effect']} |")
    for title,key in [('Commands','commands'),('States','states')]:
        table.extend(['', '## '+title, '', '| Name | Value |', '| --- | --- |'])
        table.extend(f'| {n} | {v} |' for n,v in s[key].items())
    for name,p in s.get('gp_control_profiles',{}).items():
        table.extend(['','## '+name,'',p['status']+'; confirmed '+p['confirmation']['date']+'. '+p['deployment']['status']+'.',
                      '', 'Only this register/field subset is frozen for this profile; unlisted global entries remain Draft.',
                      '', '| Offset | Approved register | Profile field restriction | Profile reset |', '| --- | --- | --- | --- |'])
        regs={r['name']:r for r in s['registers']}
        for n in p['supported_registers']:
            r=regs[n]; fields=', '.join(p['field_restrictions'].get(n,[])) or 'all defined fields'
            reset=p['reset_overrides'].get(n,r['reset'])
            table.append(f'| 0x{r["offset"]:03X} | {n} | {fields} | 0x{reset:08X} |')
        table.extend(['','Supported commands: '+', '.join(p['supported_commands'])+'.',
                      'Supported ACK errors: '+', '.join(p['supported_errors'])+'.',
                      'INIT/NOT_READY only; CAPS axis slots do not authorize motion. See '+p['documentation']+' and schema profile for complete semantics.'])
    for name,p in s.get('dma_loopback_profiles',{}).items():
        a=p['address'];irq=p['irq']
        table.extend(['','## '+name,'',p['status']+'; confirmed '+p['confirmation']['date']+'.',
                      '',f"Window 0x{a['base']:08X}/0x{a['size']:X}; register span 0x{a['register_span']:X}; full aligned D32 writes only.",
                      f"MM2S line {irq['mm2s_line']}/SPI{irq['mm2s_spi']}; S2MM line {irq['s2mm_line']}/SPI{irq['s2mm_spi']}; {irq['trigger']}.",
                      f"Shared {p['clock_hz']}Hz; stream {p['stream_width']}bit; FIFO {p['fifo_depth']} beats; transfer {p['minimum_transfer_bytes']}..{p['maximum_transfer_bytes']} bytes.",
                      '', 'Native vendor register behavior with the profile guard; no motion record layout is frozen.',
                      '', '| Offset | DMA register |', '| --- | --- |'])
        table.extend(f'| 0x{v:03X} | {n} |' for n,v in p['control_registers'].items())
    for name,p in s.get('motion_integration_profiles',{}).items():
        table+=['','## '+name,'',p['status']+'; confirmed '+p['confirmation']['date']+'.','',f"Independent window 0x{p['base']:08X}/4KiB, IRQ{p['irq_line']}/SPI{p['irq_spi']}; S2MM telemetry unsupported.",'','| Offset | Register | Access |','| --- | --- | --- |']
        table += [f'| 0x{o:03X} | {n} | {p["register_access"][n]} |' for n,o in p['registers'].items()]
    err=['<!-- '+banner+' -->','# Error candidate table','','| Code | Name | Severity | State impact | Report |','| --- | --- | --- | --- | --- |']
    err += [f"| 0x{e['value']:04X} | {e['name']} | {e['severity']} | {e['impact']} | {e['report']} |" for e in s['errors']]
    return {'interface_defs.h':'\n'.join(c),'interface_defs.vh':'\n'.join(v),'registers.md':'\n'.join(table)+'\n','errors.md':'\n'.join(err)+'\n'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    result=outputs(load()); directory=ROOT/'generated'
    if args.check:
        for n,t in result.items():
            if not (directory/n).exists() or (directory/n).read_bytes()!=t.encode('utf-8'):raise SystemExit('stale generated file: '+n)
        print('4 generated files match schema byte-for-byte')
    else:
        directory.mkdir(exist_ok=True)
        for n,t in result.items():(directory/n).write_bytes(t.encode('utf-8'))
        print('generated 4 files')

if __name__=='__main__':main()
