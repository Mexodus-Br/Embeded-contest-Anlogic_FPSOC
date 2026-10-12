"""Receive raw cold-boot evidence; never sends data or toggles DTR/RTS."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.host-python'))
import serial

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', default='COM4')
    p.add_argument('--seconds', type=float, default=300)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--stop-file', type=Path,
                   help='Finish and save metadata when this host file appears')
    a = p.parse_args()
    if a.seconds <= 0:
        p.error('seconds must be positive')
    s = serial.Serial(port=None, baudrate=115200, bytesize=8,
                      parity='N', stopbits=1, timeout=0.2,
                      xonxoff=False, rtscts=False, dsrdtr=False)
    s.dtr = False
    s.rts = False
    start = datetime.now(timezone.utc).isoformat()
    count = 0
    digest = hashlib.sha256()
    # Exclusive creation prevents overwriting an earlier board evidence log.
    with a.log.open('xb') as output:
        try:
            s.port = a.port
            s.open()
            print('SERIAL_CAPTURE_READY: user may perform authorized cold boot', flush=True)
            deadline = time.monotonic() + a.seconds
            while time.monotonic() < deadline:
                if a.stop_file and a.stop_file.exists():
                    break
                chunk = s.read(65536)
                if chunk:
                    output.write(chunk)
                    output.flush()
                    digest.update(chunk)
                    count += len(chunk)
        except KeyboardInterrupt:
            pass
        finally:
            s.close()
            metadata = {'start_utc': start, 'end_utc': datetime.now(timezone.utc).isoformat(),
                        'port': a.port, 'baud': 115200, 'format': '8N1', 'dtr': False,
                        'rts': False, 'sent_bytes': 0, 'received_bytes': count,
                        'sha256': digest.hexdigest()}
            a.log.with_suffix(a.log.suffix + '.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metadata), flush=True)

if __name__ == '__main__':
    main()
