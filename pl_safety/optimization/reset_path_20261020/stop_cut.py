"""Exact private-control cofactor; no added cycle or changed state priority."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
if __name__=='__main__':
    out=HERE/'stop_candidate_r1';out.mkdir(exist_ok=False)
    s=(ROOT/'pl_motion/rtl/motion_service.v').read_text()
    old=''' wire stop_kernel=(private_stop && !safety_stop_seen && occupied) || stop_write ||
  ((|fault || !reset_ok || req_disable) && occupied) ||
  (dma_error ? occupied : rx_without_dma);'''
    new=''' // With any private control asserted, receiver.error is necessarily zero.
 // Select the exact cofactor here instead of routing safety_stop through
 // receiver abort/error and back into the executor stop controls.
 wire private_abort=private_stop || private_disable || (HOME_SUPPORT && home_enable);
 wire common_stop=(|fault) || !reset_ok || req_disable;
 wire rx_without_private=rst_n && !(stop_write || common_stop || cancelled || session_done) && rx_error_candidate;
 wire stop_private=stop_write || ((common_stop || dma_error || (private_stop && !safety_stop_seen)) && occupied);
 wire stop_public=stop_write || (common_stop && occupied) || (dma_error ? occupied:rx_without_private);
 wire stop_kernel=private_abort ? stop_private:stop_public;'''
    assert s.count(old)==1
    (out/'motion_service.v').write_text(s.replace(old,new))
    for v in range(65536):
        P,Q,HS,H,SEEN,O,S,F,R,I,C,DONE,RST,E,D,spare=[bool((v>>b)&1) for b in range(16)]
        A=P or Q or (HS and H)
        old_rx=RST and not(P or Q or (HS and H) or S or F or not R or I or C or DONE) and E
        old_stop=(P and not SEEN and O) or S or ((F or not R or I) and O) or (O if D else old_rx)
        common=F or not R or I
        new_rx=RST and not(S or common or C or DONE) and E
        new_stop=(S or ((common or D or (P and not SEEN)) and O)) if A else (S or (common and O) or (O if D else new_rx))
        assert bool(old_stop)==bool(new_stop),v
    (out/'boolean.json').write_text(json.dumps({'passed':True,'combinations':65536,'hashes_computed':False},indent=2)+'\n')
    print('PASS exact stop cofactor all 65536 Boolean combinations')
