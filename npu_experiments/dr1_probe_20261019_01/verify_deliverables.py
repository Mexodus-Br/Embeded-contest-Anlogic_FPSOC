"""Replay fixed host vectors and audit final configuration/resource evidence."""
from pathlib import Path
import json
import re
import numpy as np
import onnx
import onnxruntime as ort

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    checks=[]
    for kind in ['uint8','int8']:
        p=ROOT/f'models/probe_a_trained_al4d_sim_quant_{kind}.onnx'
        m=onnx.load(p);onnx.checker.check_model(m)
        assert len(m.graph.input)==1 and len(m.graph.node)>3
        opts=ort.SessionOptions();opts.intra_op_num_threads=1;opts.inter_op_num_threads=1
        sess=ort.InferenceSession(str(p),sess_options=opts,providers=['CPUExecutionProvider'])
        v=np.load(ROOT/f'models/probe_a_{kind}_vectors.npz')
        y=np.concatenate([sess.run(None,{'input':x[None]})[0] for x in v['input']])
        np.testing.assert_allclose(y,v['quantized_host_output'],rtol=1e-5,atol=1e-5)
        assert np.ptp(y,axis=0).max()>.01
        checks.append(kind+' fixed vectors replayed on CPU; input-dependent')
    q=json.loads((ROOT/'models/quantization_results.json').read_text())
    d=np.load(ROOT/'data/features_and_splits.npz')
    assert not set(d['train']) & set(d['validation'])
    assert not set(d['train']) & set(d['test'])
    assert not set(d['validation']) & set(d['test'])
    for kind in ['uint8','int8']:
        assert len(q[kind]['calibration_cycles'])==500
        assert set(q[kind]['calibration_cycles']) <= set(d['train'])
    checks.append('cycle splits mutually exclusive; calibration train-only')
    rs=json.loads((ROOT/'resource_results.json').read_text())
    assert len(rs['configurations'])==5
    for row in rs['configurations']:
        assert row['virtual_io']==433 and row['eram']>0 and row['registers']>1000
        assert row['lut6_equivalent_gate']==row['slice_gate']-row['register_only_slices']
        assert row['ip_body_lut6_equivalent_gate']+row['virtual_boundary_lut6_equivalent_gate']==row['lut6_equivalent_gate']
    for name in ['full_native','whole_no_video','tiny_no_video','mbface_no_video','v3_no_video']:
        folder=ROOT/('audit100_'+name)
        timing=(folder/'gate_100m.timing').read_text()
        active=re.findall(r'^\s*clk\d+:\s+([\d.]+)\s+\d+\s+(npu_\w+)',timing,re.M)
        assert sorted(active)==[('100.000','npu_config'),('100.000','npu_data')]
        assert 'DeriveClock' not in timing
        status=json.loads((folder/'status.json').read_text())
        assert status['input_db_unchanged'] and status['threads']==16
    checks.append('five nonempty mapped configurations; top/core counters separated; actual STA clocks read back at 100MHz')
    route=rs['independent_route']
    assert route['active_clock_mhz']==100 and route['setup_ns']>0 and route['hold_ns']>=0
    assert route['lut6_equivalent']==11105 and route['slice']==11931
    assert route['arithmetic_budget']['slice']['remaining']==2565
    state=json.loads((ROOT/'physical_tiny_route100/status.json').read_text())
    assert state['threads']==16 and state['input_place_db_unchanged']
    checks.append('isolated Tiny route completed at 100MHz; no integrated closure claim')
    result=dict(passed=True,checks=checks,host_only_numeric_verification=True,
                npu_execution_verified=False,integrated_system_verified=False)
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
