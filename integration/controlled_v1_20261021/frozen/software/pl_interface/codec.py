"""Reference record codec; no execution or mechanical-validity claim."""
import argparse, json, struct, zlib
from pathlib import Path
from generate import load

SPEC=load()
FMT={'u8':'B','u16':'H','u32':'I','u64':'Q','i64':'q','bytes16':'16s'}

def check_fields(kind,v):
    if kind=='motion':
        if not v['session_id']:raise ValueError('zero motion session')
        for i in range(4):
            if not v['axis_mask']&(1<<i) and v['target'+str(i)]!=0:raise ValueError('inactive target')
    else:
        if v['error_code'] not in {e['value'] for e in SPEC['errors']}:raise ValueError('unknown error')
        if v['raw'][v['raw_length']:]!=bytes(16-v['raw_length']):raise ValueError('raw padding')
        if not v['validity']&1 and v['command_position']:raise ValueError('invalid command position')
        if not v['validity']&2:
            if v['feedback_raw'] or v['sample_tick'] or v['age_tick']!=2**64-1:raise ValueError('missing sample')
        elif v['sample_tick']>v['event_tick'] or v['age_tick']!=v['event_tick']-v['sample_tick']:
            raise ValueError('sample age/epoch')
        if v['validity']&8 and (v['validity']&6)!=6:raise ValueError('fresh without communication/sample')

def field_check(x,value):
    if 'constant' in x and value!=x['constant']:raise ValueError('constant '+x['name'])
    if 'allowed_mask' in x and value&~x['allowed_mask']:raise ValueError('reserved bits')
    if 'min' in x and value<x['min']:raise ValueError('minimum')
    if 'max' in x and value>x['max']:raise ValueError('maximum')
    if 'enum' in x and value not in x['enum']:raise ValueError('enum')

def encode(kind,values):
    f=SPEC['frames'][kind]; known={x['name'] for x in f['fields']}
    if set(values)-known:raise ValueError('unknown fields')
    data=bytearray(f['length'])
    for x in f['fields'][:-1]:
        default=bytes(16) if x['type']=='bytes16' else (2**32-1 if kind=='telemetry' and x['name']=='motion_seq' else 0)
        value=values.get(x['name'],x.get('constant',default))
        if x['type']=='bytes16' and (not isinstance(value,bytes) or len(value)!=16):raise ValueError('raw must be 16 bytes')
        field_check(x,value)
        try:struct.pack_into('<'+FMT[x['type']],data,x['offset'],value)
        except (struct.error,TypeError) as exc:raise ValueError('field range/type: '+x['name']) from exc
    struct.pack_into('<I',data,len(data)-4,zlib.crc32(data[:-4]))
    decode(kind,data)
    return bytes(data)

def decode(kind,data):
    f=SPEC['frames'][kind]
    if len(data)!=f['length']:raise ValueError('record length')
    if zlib.crc32(data[:-4])!=struct.unpack_from('<I',data,len(data)-4)[0]:raise ValueError('CRC')
    values={}
    for x in f['fields']:
        value=struct.unpack_from('<'+FMT[x['type']],data,x['offset'])[0]
        field_check(x,value);values[x['name']]=value
    check_fields(kind,values)
    return values

def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=SPEC['frames']);p.add_argument('operation',choices=['encode','decode']);p.add_argument('input');a=p.parse_args()
    if a.operation=='encode':
        v=json.loads(Path(a.input).read_text(encoding='utf-8'))
        if 'raw' in v:v['raw']=bytes.fromhex(v['raw'])
        print(encode(a.kind,v).hex())
    else:
        v=decode(a.kind,bytes.fromhex(Path(a.input).read_text()))
        if 'raw' in v:v['raw']=v['raw'].hex()
        print(json.dumps(v,indent=2))

if __name__=='__main__':main()
