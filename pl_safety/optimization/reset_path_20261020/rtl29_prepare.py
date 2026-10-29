"""Remove reset only from private telemetry frame/CRC payload, never VALID/owner."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl29_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl28_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 s=(R/'pl_rs485/rtl/rs485_telemetry.v').read_text()
 s=replace(s,'frame<=0;crc<=0;','')
 s=replace(s,"LOAD:begin frame<={32'd0,head[479:0]};crc<=`RT_CRC_INIT;byte_index<=0;state<=CRC;end",
  'LOAD:begin byte_index<=0;state<=CRC;end')
 s=replace(s,'CRC:begin crc<=crc_byte(crc,frame[byte_index*8+:8]);','CRC:begin')
 s=replace(s,"frame[511:480]<=crc_byte(crc,frame[byte_index*8+:8])^`RT_CRC_XOROUT;beat<=0;",'beat<=0;')
 extra='''
// Packet state/credits/generation and VALID remain asynchronously invalidated.
// LOAD replaces all frame bits and initializes CRC before any SEND ownership;
// CRC completes before VALID. Reset/cancel never publishes retained data.
// Invalid AXIS DATA is unspecified, as permitted by the unchanged VALID contract.
always @(posedge clk)begin
 if(state==LOAD)begin frame<={32'd0,head[479:0]};crc<=`RT_CRC_INIT;end
 else if(state==CRC)begin
  crc<=crc_byte(crc,frame[byte_index*8+:8]);
  if(byte_index==`RT_CRC_BYTES-1)
   frame[511:480]<=crc_byte(crc,frame[byte_index*8+:8])^`RT_CRC_XOROUT;
 end
end
'''
 (out/'rs485_telemetry.v').write_text(s.replace('endmodule',extra+'endmodule'))
 (out/'transport_notes.json').write_text(json.dumps({'hashes_computed':False,'additional_source_async_bits_removed':544,
  'unchanged':'all packet/generation/credit/VALID/control reset, FIFO256 and atomic packet framing, CRC and timing',
  'invalid_only':'DATA/CRC private payload may retain old values while VALID=0; LOAD overwrites before SEND',
  'status':'isolated module validation pending'},indent=2)+'\n')
 print('Prepared RTL29 private telemetry payload reset removal')
if __name__=='__main__':main()
