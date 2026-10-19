"""Run unmodified SDK AL tools, with an explicit non-image calibration reader.

The rank-4 -> Flatten boundary and transposed constant Gemm weights preserve the
68-vector MLP. No capability check, backend, or RTL is replaced.
"""
from pathlib import Path
import json
import sys
import subprocess
import os
import numpy as np
import onnx
from onnx import helper, numpy_helper, shape_inference

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / 'sdk2025_reference/sdk/app/npu/scripts'
sys.path.insert(0, str(VENDOR))


def save_log(name, args):
    with (ROOT/name).open('w', encoding='utf-8') as f:
        r = subprocess.run([sys.executable, *args], stdout=f, stderr=subprocess.STDOUT)
    return r.returncode


def adapted_model(source, dest, four_d=False):
    m = onnx.load(source)
    transposed = set()
    for n in m.graph.node:
        if n.op_type == 'Gemm':
            for a in n.attribute:
                if a.name == 'transB': a.i = 1
            transposed.add(n.input[1])
    for i, t in enumerate(m.graph.initializer):
        if t.name in transposed:
            m.graph.initializer[i].CopyFrom(numpy_helper.from_array(numpy_helper.to_array(t).T.copy(), t.name))
    if four_d:
        m.graph.input[0].CopyFrom(helper.make_tensor_value_info('input', onnx.TensorProto.FLOAT, [1,68,1,1]))
        m.graph.node[0].input[0] = 'flat_input'
        m.graph.node.insert(0, helper.make_node('Flatten', ['input'], ['flat_input'], axis=1, name='feature_boundary'))
    m = shape_inference.infer_shapes(m)
    onnx.checker.check_model(m)
    onnx.save(m, dest)
    return m


if __name__ == '__main__':
    import onnxruntime as ort
    modeldir = ROOT/'models'
    orig = modeldir/'probe_a_seed_fp32.onnx'
    onnx.save(shape_inference.infer_shapes(onnx.load(orig)), modeldir/'probe_a_seed_inferred.onnx')
    status = {}
    status['original_transB0_checker_exit'] = save_log('check_seed_transB0.log', [str(VENDOR/'check_onnx_model.py'), '--input_model', str(modeldir/'probe_a_seed_inferred.onnx')])
    model2 = modeldir/'probe_a_seed_transB1.onnx'
    adapted_model(orig, model2)
    status['transB1_checker_exit'] = save_log('check_seed_transB1.log', [str(VENDOR/'check_onnx_model.py'), '--input_model', str(model2)])
    status['two_dimensional_AL_entry_exit'] = save_log('al_entry_2d.log', [str(VENDOR/'AL_onnx_pass.py'), '--input_model', str(model2), '--calibrate_dataset', str(ROOT/'data'), '--quant_type', 'uint8'])
    src = modeldir/'probe_a_trained_fp32.onnx'; target=modeldir/'probe_a_trained_al4d.onnx'
    adapted_model(src, target, four_d=True)
    original_session = ort.InferenceSession(str(src), providers=['CPUExecutionProvider'])
    adapted_session = ort.InferenceSession(str(target), providers=['CPUExecutionProvider'])
    d = np.load(ROOT/'data/features_and_splits.npz')
    x = d['standardized_features']; ids = d['test'][:8]
    y1 = np.concatenate([original_session.run(None, {'input': a[None]})[0] for a in x[ids]])
    y2 = np.concatenate([adapted_session.run(None, {'input': a.reshape(1,68,1,1)})[0] for a in x[ids]])
    np.testing.assert_allclose(y1,y2,rtol=1e-5,atol=1e-5)
    status['rank4_boundary_max_abs_error'] = float(np.max(np.abs(y1-y2)))
    status['rank4_checker_exit'] = save_log('check_trained_al4d.log', [str(VENDOR/'check_onnx_model.py'), '--input_model', str(target)])
    status['sdk_script_directory'] = str(VENDOR)
    status['sdk_software_pipeline'] = 'AL ONNX -> Arm NN Alnpu runtime, not the UG1214 tmfile pipeline'
    status['hardware_execution'] = False
    (ROOT/'al_probe_status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status,indent=2))
