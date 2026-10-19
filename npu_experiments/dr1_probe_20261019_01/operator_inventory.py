"""Complete exported ONNX node inventory; runtime assignment remains unknown."""
from pathlib import Path
import csv,json
import onnx

ROOT=Path(__file__).resolve().parent
rows=[]
for model in sorted((ROOT/'models').glob('*.onnx')):
    m=onnx.load(model)
    for node in m.graph.node:
        if node.op_type in ['Gemm','Relu']:
            candidate='Hard candidate: UG1214 + SDK checker, not runtime-verified'
        elif node.op_type in ['QuantizeLinear','DequantizeLinear']:
            candidate='Quantization metadata/fusion candidate; backend instruction assignment not obtained'
        elif node.op_type in ['Flatten','Reshape']:
            candidate='Layout/view candidate; host check passed for A, runtime mapping unknown'
        elif node.op_type=='GlobalAveragePool':
            candidate='SDK checker warns ALNPU cannot accelerate; PS partition/fallback not validated'
        elif node.op_type=='Conv':
            candidate='B rank3 rejected / 1x3 warned / zero-embedded 3x3 checker permitted; runtime unverified'
        else:
            candidate='Unverified'
        rows.append(dict(model=model.name,node=node.name,operator=node.op_type,
                         inputs=';'.join(node.input),outputs=';'.join(node.output),
                         candidate=candidate,actual_execution='unverified: no NPU execution or backend instruction graph'))
with (ROOT/'operator_assignment.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(ROOT/'placement_status.json').write_text(json.dumps(dict(
    actual_hard_assignments=[],actual_soft_assignments=[],actual_cpu_fallback_assignments=[],
    sdk_checker_soft_requirements_for_probe_a=[],
    empty_checker_list_does_not_prove_hard_only_deployment=True,
    ps_planned_operations=['native-rate cycle statistics','train-derived normalization','argmax/diagnostic interpretation'],
    runtime_backend='Alnpu, optionally CpuAcc/CpuRef in vendor example; per-node assignments not obtained',
    latency='not measured',hardware_execution=False),indent=2)+'\n')
print('inventoried',len(rows),'ONNX nodes')
