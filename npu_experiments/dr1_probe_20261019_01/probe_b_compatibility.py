"""Untrained B geometry probes; verify Conv1D lowering without claiming NPU use."""
from pathlib import Path
import sys,json,subprocess
import numpy as np
import onnx
from onnx import helper as h,numpy_helper as nh,TensorProto as T,shape_inference
from onnx.reference import ReferenceEvaluator

ROOT=Path(__file__).resolve().parent
CHECK=ROOT/'sdk2025_reference/sdk/app/npu/scripts/check_onnx_model.py'
rng=np.random.default_rng(20261019)
w0=rng.normal(0,.1,(16,17,3)).astype(np.float32)
w1=rng.normal(0,.1,(32,16,3)).astype(np.float32)
fc=rng.normal(0,.1,(3,32)).astype(np.float32)
b0=rng.normal(0,.01,16).astype(np.float32)
b1=rng.normal(0,.01,32).astype(np.float32)
bc=rng.normal(0,.01,3).astype(np.float32)

def make(kind):
    if kind=='conv1d':
        ww=[w0,w1];shape=[1,17,128];kernel=[3];pads=[1,1];strides=[1];dilations=[1]
    elif kind=='conv2d_1x3':
        ww=[w0[:,:,None,:],w1[:,:,None,:]];shape=[1,17,1,128];kernel=[1,3];pads=[0,1,0,1];strides=[1,1];dilations=[1,1]
    else:
        ww=[]
        for w in [w0,w1]:
            v=np.zeros((*w.shape[:2],3,3),np.float32);v[:,:,1,:]=w;ww.append(v)
        shape=[1,17,1,128];kernel=[3,3];pads=[1,1,1,1];strides=[1,1];dilations=[1,1]
    nodes=[];init=[];current='input'
    for i,(w,b) in enumerate(zip(ww,[b0,b1])):
        init.extend([nh.from_array(w,f'w{i}'),nh.from_array(b,f'b{i}')])
        nodes.extend([h.make_node('Conv',[current,f'w{i}',f'b{i}'],[f'z{i}'],name=f'conv{i}',
                                 kernel_shape=kernel,pads=pads,strides=strides,dilations=dilations),
                      h.make_node('Relu',[f'z{i}'],[f'a{i}'],name=f'relu{i}')]);current=f'a{i}'
    nodes.extend([h.make_node('GlobalAveragePool',[current],['mean'],name='temporal_mean'),
                  h.make_node('Flatten',['mean'],['flat'],name='flatten',axis=1),
                  h.make_node('Gemm',['flat','fc','bc'],['output'],name='classifier',transB=1)])
    init.extend([nh.from_array(fc,'fc'),nh.from_array(bc,'bc')])
    graph=h.make_graph(nodes,kind,[h.make_tensor_value_info('input',T.FLOAT,shape)],
                       [h.make_tensor_value_info('output',T.FLOAT,[1,3])],init)
    m=h.make_model(graph,opset_imports=[h.make_opsetid('',13)]);m.ir_version=8
    m=shape_inference.infer_shapes(m);onnx.checker.check_model(m)
    return m

if __name__=='__main__':
    results={};x=rng.normal(size=(1,17,128)).astype(np.float32);reference=None
    out=ROOT/'models'
    for kind in ['conv1d','conv2d_1x3','conv2d_3x3_zero_embed']:
        m=make(kind);p=out/f'probe_b_{kind}.onnx';onnx.save(m,p)
        y=ReferenceEvaluator(m).run(None,{'input':x if kind=='conv1d' else x[:,:,None,:]})[0]
        if reference is None:reference=y
        np.testing.assert_allclose(y,reference,rtol=1e-5,atol=1e-6)
        log=ROOT/f'check_b_{kind}.log'
        with log.open('w',encoding='utf-8') as f:
            r=subprocess.run([sys.executable,str(CHECK),'--input_model',str(p)],stdout=f,stderr=subprocess.STDOUT)
        results[kind]=dict(checker_exit=r.returncode,stored_parameters=sum(nh.to_array(t).size for t in m.graph.initializer),
                           original_parameters=2499,original_logical_macs=301152,
                           lowering_max_abs_reference_error=float(np.max(np.abs(y-reference))),
                           zero_embedded_conv_macs=903264 if kind.endswith('embed') else None,
                           graph_operators=[dict(name=n.name,type=n.op_type) for n in m.graph.node],
                           trained=False,npu_execution=False)
    np.savez(out/'probe_b_lowering_vectors.npz',input=x,output=reference)
    (out/'probe_b_compatibility.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
