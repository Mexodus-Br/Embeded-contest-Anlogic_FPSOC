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
    for n,f in s['frames'].items():
        occupied=set(); fieldnames=set()
        for x in f['fields']:
            if x['name'] in fieldnames:raise ValueError('duplicate frame field')
            fieldnames.add(x['name']); size=SIZES[x['type']]
            occupied_new=set(range(x['offset'],x['offset']+size))
            if occupied&occupied_new or min(occupied_new)<0 or max(occupied_new)>=f['length']:raise ValueError('frame overlap/range')
            occupied |= occupied_new
        if occupied!=set(range(f['length'])) or f['fields'][-1]['name']!='crc' or f['fields'][-1]['offset']!=f['length']-4:raise ValueError('frame gap/crc')

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
    banner='Generated from schema.json SHA256 '+digest+'; DRAFT semantics.'
    c=['/* '+banner+' */','#ifndef PL_INTERFACE_DEFS_H','#define PL_INTERFACE_DEFS_H','#include <stdint.h>']
    v=['// '+banner,'`ifndef PL_INTERFACE_DEFS_VH','`define PL_INTERFACE_DEFS_VH']
    for n,val in constants(s).items():
        c.append(f'#define PLI_{n} UINT32_C(0x{val:08X})')
        v.append(f'`define PLI_{n} 32\'h{val:08X}')
    c.extend(['#endif','']); v.extend(['`endif',''])
    table=['<!-- '+banner+' -->','# Register candidate table','', '| Offset | Name | Width | Reset | Access | Fields | Unit | Side effect |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in s['registers']:
        fields=', '.join(f"{x['name']}[{x['lsb']+x['width']-1}:{x['lsb']}]" for x in r['fields'])
        table.append(f"| 0x{r['offset']:03X} | {r['name']} | 32 | 0x{r['reset']:08X} | {r['access']} | {fields} | {r['unit']} | {r['effect']} |")
    for title,key in [('Commands','commands'),('States','states')]:
        table.extend(['', '## '+title, '', '| Name | Value |', '| --- | --- |'])
        table.extend(f'| {n} | {v} |' for n,v in s[key].items())
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
