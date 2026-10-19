"""Count test activation values beyond calibrated ranges; no NPU timing."""
from pathlib import Path
import json
import numpy as np
import onnx
import onnxruntime as ort

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    data=np.load(ROOT/'data/features_and_splits.npz');ids=data['test'];x=data['standardized_features'][ids]
    results={}
    for kind in ['uint8','int8']:
        model=onnx.load(ROOT/f'models/probe_a_trained_al4d_sim_quant_{kind}.onnx')
        constants={t.name:onnx.numpy_helper.to_array(t) for t in model.graph.initializer}
        qnodes=[n for n in model.graph.node if n.op_type=='QuantizeLinear']
        inferred=onnx.shape_inference.infer_shapes(model)
        info={t.name:t for t in [*inferred.graph.value_info,*inferred.graph.output]}
        for node in qnodes:
            model.graph.output.append(info[node.input[0]])
        opts=ort.SessionOptions();opts.intra_op_num_threads=1;opts.inter_op_num_threads=1
        sess=ort.InferenceSession(model.SerializeToString(),sess_options=opts,providers=['CPUExecutionProvider'])
        samples=[sess.run([n.input[0] for n in qnodes],{'input':a.reshape(1,68,1,1)}) for a in x]
        result={}
        for i,node in enumerate(qnodes):
            values=np.concatenate([a[i].reshape(-1) for a in samples])
            scale=constants[node.input[1]];zp=constants[node.input[2]]
            limits=np.iinfo(zp.dtype);lo=float((limits.min-float(zp))*scale);hi=float((limits.max-float(zp))*scale)
            unclipped=np.rint(values/scale)+float(zp)
            result[node.input[0]]=dict(elements=len(values),range_low=lo,range_high=hi,
                values_outside_range=int(((values<lo)|(values>hi)).sum()),
                values_below_range=int((values<lo).sum()),values_above_range=int((values>hi).sum()),
                rounded_values_clipped=int(((unclipped<limits.min)|(unclipped>limits.max)).sum()),
                rounded_low_clipped=int((unclipped<limits.min).sum()),
                rounded_high_clipped=int((unclipped>limits.max).sum()),
                expected_relu_low_clamp=(kind=='uint8' and node.input[0] in ['a0','a1']),
                interpretation='Observed CPU QDQ activation inputs over held-out full cycles; not a hardware saturation counter')
        results[kind]=result
    (ROOT/'models/saturation_analysis.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
