"""Execute SDK AL_onnx_pass unchanged, adapting only its image data reader.

Uses train-cycle feature vectors (500 maximum), SDK QDQ policies and official
split/check functions. This produces ONNX, not a validated NPU instruction graph.
"""
from pathlib import Path
import sys
import runpy
import json
import contextlib
import collections
import logging
import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader

ROOT=Path(__file__).resolve().parent
VENDOR=ROOT/'sdk2025_reference/sdk/app/npu/scripts'
sys.path.insert(0,str(VENDOR))
import data_reader


def calibration_ids(data):
    rng=np.random.default_rng(20261019)
    train=data['train']; labels=data['labels']; selected=[]
    for label in range(3):
        available=train[labels[train]==label]
        count=int(500*len(available)/len(train)) if label<2 else 500-len(selected)
        selected.extend(rng.permutation(available)[:count].tolist())
    ids=np.array(selected,dtype=np.int64)
    assert len(ids)==500 and set(ids)<=set(train)
    return rng.permutation(ids)


class FeatureReader(CalibrationDataReader):
    def __init__(self, calibration_dataset_path, model_path, mean, scale):
        data=np.load(ROOT/'data/features_and_splits.npz')
        self.ids=calibration_ids(data)
        self.x=data['standardized_features'][self.ids]
        self.name=ort.InferenceSession(model_path,providers=['CPUExecutionProvider']).get_inputs()[0].name
        self.rewind()
    def get_next(self):
        return next(self.iterator,None)
    def rewind(self):
        self.iterator=iter([{self.name:a.reshape(1,68,1,1)} for a in self.x])


if __name__=='__main__':
    # SDK README explicitly permits changing preprocessing for non-image models.
    # Only data ingestion changes; SDK transformations/checks/quantization stay intact.
    data_reader.DataReader=FeatureReader
    d=np.load(ROOT/'data/features_and_splits.npz'); x=d['standardized_features']; y=d['labels']; test=d['test']
    root=ROOT/'models'; model=root/'probe_a_trained_al4d.onnx'
    results={}
    opt=ort.SessionOptions(); opt.intra_op_num_threads=1; opt.inter_op_num_threads=1
    def infer(path,ids):
        s=ort.InferenceSession(str(path),sess_options=opt,providers=['CPUExecutionProvider'])
        return np.concatenate([s.run(None,{'input':a.reshape(1,68,1,1)})[0] for a in x[ids]])
    floating=infer(model,test)
    for qt in ['uint8','int8']:
        sys.argv=[str(VENDOR/'AL_onnx_pass.py'),'--input_model',str(model),
                  '--calibrate_dataset',str(ROOT/'data'),'--quant_type',qt]
        with (ROOT/f'al_pass_{qt}.log').open('w',encoding='utf-8') as log:
            with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                logging.basicConfig(stream=log, force=True)
                runpy.run_path(str(VENDOR/'AL_onnx_pass.py'),run_name='__main__')
        path=root/f'probe_a_trained_al4d_sim_quant_{qt}.onnx'
        m=onnx.load(path);onnx.checker.check_model(m)
        actual=infer(path,test)
        scale_values={t.name:onnx.numpy_helper.to_array(t).tolist() for t in m.graph.initializer
                      if any(s in t.name for s in ['scale','zero_point'])}
        ops=[dict(name=n.name,type=n.op_type,inputs=list(n.input),outputs=list(n.output)) for n in m.graph.node]
        results[qt]=dict(test_accuracy=float((actual.argmax(1)==y[test]).mean()),
                        prediction_agreement=float((actual.argmax(1)==floating.argmax(1)).mean()),
                        max_abs_logit_error=float(np.max(np.abs(actual-floating))),
                        mean_abs_logit_error=float(np.abs(actual-floating).mean()),
                        operators=ops,operator_counts=dict(collections.Counter(n.op_type for n in m.graph.node)),
                        scales_zero_points=scale_values,
                        calibration_cycles=calibration_ids(d).tolist(),
                        calibration_class_counts=np.bincount(y[calibration_ids(d)],minlength=3).tolist(),
                        sdk_policy='SDK run_quant.py: QDQ min/max, UINT8 per-tensor; INT8 per-channel symmetric',
                        npu_execution=False,npu_latency='not measured')
        np.savez(root/f'probe_a_{qt}_vectors.npz',cycle_ids=test[:8],input=x[test[:8]].reshape(8,68,1,1),
                 float_output=floating[:8],quantized_host_output=actual[:8])
    results['float_accuracy']=float((floating.argmax(1)==y[test]).mean())
    (root/'quantization_results.json').write_text(json.dumps(results,indent=2)+'\n')
    print({k:{kk:vv for kk,vv in v.items() if kk in ['test_accuracy','prediction_agreement','max_abs_logit_error']}
           for k,v in results.items() if isinstance(v,dict)})
