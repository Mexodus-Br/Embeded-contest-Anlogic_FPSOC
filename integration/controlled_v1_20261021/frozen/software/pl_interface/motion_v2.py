"""Executable motion_stream_v2 codec; legacy Draft codecs remain unchanged."""
import json,struct,zlib
from pathlib import Path
SCHEMA=json.loads((Path(__file__).parent/'schema.json').read_text(encoding='utf-8'))
PROFILE=SCHEMA['motion_integration_profiles']['gp_motion_v1']
FRAME=SCHEMA['frames']['motion_stream_v2']
FORMATS={'u16':'H','u32':'I','u64':'Q','i64':'q'}
def validate(v):
    if not 0<v['session_id']<2**64 or not 0<=v['sequence']<2**32:raise ValueError('session/sequence')
    if v['flags'] not in (0,1) or not 0<=v['axis_mask']<16:raise ValueError('flags/mask')
    if not 0<v['duration_tick']<=(2**64-1)//PROFILE['cycles_per_tick']:raise ValueError('duration overflow')
    for i in range(4):
        x=v['target'+str(i)]
        if not -2**63<=x<2**63 or (not (v['axis_mask']>>i)&1 and x):raise ValueError('target')
def encode(v):
    validate(v);b=bytearray(FRAME['length'])
    for f in FRAME['fields']:
        if f['name']=='crc':continue
        struct.pack_into('<'+FORMATS[f['type']],b,f['offset'],f['constant'] if 'constant' in f else v[f['name']])
    struct.pack_into('<I',b,FRAME['fields'][-1]['offset'],zlib.crc32(b[:-4]))
    return bytes(b)
def decode(b):
    if len(b)!=FRAME['length']:raise ValueError('length')
    v={f['name']:struct.unpack_from('<'+FORMATS[f['type']],b,f['offset'])[0] for f in FRAME['fields']}
    if v['crc']!=zlib.crc32(b[:-4]):raise ValueError('CRC')
    if any(v[f['name']]!=f['constant'] for f in FRAME['fields'] if 'constant' in f):raise ValueError('header/reserved')
    validate(v);return v
