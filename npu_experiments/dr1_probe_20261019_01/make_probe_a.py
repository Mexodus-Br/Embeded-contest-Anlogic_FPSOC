"""Untrained nonzero compatibility probe; no diagnostic accuracy claim."""
from pathlib import Path
import sys
import json
import importlib.util
import numpy as np

ROOT = Path(__file__).resolve().parent
if importlib.util.find_spec('onnx') is None:
    sys.path.insert(0, str(ROOT / 'env'))
import onnx
from onnx import helper as h, numpy_helper as nh, TensorProto as T
from onnx.reference import ReferenceEvaluator


def export(weights, out):
    nodes, init = [], []
    current = 'input'
    for i in range(3):
        w, b = weights[f'w{i}'], weights[f'b{i}']
        init += [nh.from_array(w, f'w{i}'), nh.from_array(b, f'b{i}')]
        dest = 'output' if i == 2 else f'z{i}'
        nodes.append(h.make_node('Gemm', [current, f'w{i}', f'b{i}'], [dest],
                                 name=f'fc{i}', alpha=1., beta=1., transB=0))
        if i < 2:
            current = f'a{i}'
            nodes.append(h.make_node('Relu', [dest], [current], name=f'relu{i}'))
    graph = h.make_graph(nodes, 'probe_a', [h.make_tensor_value_info('input', T.FLOAT, [1, 68])],
                         [h.make_tensor_value_info('output', T.FLOAT, [1, 3])], init)
    model = h.make_model(graph, opset_imports=[h.make_opsetid('', 13)], producer_name='DR1 isolated experiment')
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx.save(model, str(out))
    return model


def forward(x, weights):
    for i in range(3):
        x = x @ weights[f'w{i}'] + weights[f'b{i}']
        if i < 2:
            x = np.maximum(x, 0)
    return x


if __name__ == '__main__':
    out = ROOT / 'models'; out.mkdir(exist_ok=True)
    rng = np.random.default_rng(20261019)
    weights = {}
    for i, (a, b) in enumerate(zip([68, 32, 16], [32, 16, 3])):
        weights[f'w{i}'] = rng.normal(0, np.sqrt(2 / a), (a, b)).astype(np.float32)
        weights[f'b{i}'] = rng.normal(0, .02, b).astype(np.float32)
    assert sum(w.size for w in weights.values()) == 2787
    assert all(np.all(w != 0) for w in weights.values())
    np.savez(out / 'probe_a_seed_weights.npz', **weights)
    model = export(weights, out / 'probe_a_seed_fp32.onnx')
    xs = np.stack([np.zeros(68), np.ones(68), np.linspace(-2, 2, 68), rng.normal(size=68)]).astype(np.float32)
    ys = forward(xs, weights)
    ref = ReferenceEvaluator(model)
    actual = np.concatenate([ref.run(None, {'input': x[None]})[0] for x in xs])
    np.testing.assert_allclose(actual, ys, rtol=1e-5, atol=1e-6)
    assert np.ptp(ys, axis=0).max() > .01
    np.savez(out / 'probe_a_seed_vectors.npz', input=xs, numpy_output=ys, onnx_output=actual)
    info = dict(seed=20261019, trained=False, diagnostic_effectiveness='not evaluated',
                weights=2736, biases=51, logical_macs=2736,
                input_shape=[1, 68], operators=[{'name': n.name, 'type': n.op_type,
                'inputs': list(n.input), 'outputs': list(n.output)} for n in model.graph.node],
                max_abs_host_reference_error=float(np.max(np.abs(actual-ys))),
                live_graph_inputs=[x.name for x in model.graph.input],
                graph_nodes=5, input_dependence_verified=True,
                dr1_conversion='not run: host compiler absent; AArch64 runtime cannot run on this Windows host',
                constant_folding_after_dr1_conversion='not verifiable without conversion output',
                quantized_model='not yet generated; representative calibration data required')
    (out / 'probe_a_seed_manifest.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))
