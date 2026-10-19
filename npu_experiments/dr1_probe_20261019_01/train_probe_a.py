"""Small CPU reference experiment; never reports CPU execution as DR1 execution.

Data: Helwig, Pignanelli, Schuetze, UCI 447, DOI 10.24432/C5CW21,
CC BY 4.0. Original 60-second cycles are indivisible split units.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
from pathlib import Path
import json
from zipfile import ZipFile
import numpy as np
from make_probe_a import export, forward

ROOT = Path(__file__).resolve().parent
SENSORS = [('PS'+str(i), 100) for i in range(1, 7)] + [('EPS1', 100),
           ('FS1', 10), ('FS2', 10)] + [('TS'+str(i), 1) for i in range(1, 5)] + [
           ('VS1', 1), ('CE', 1), ('CP', 1), ('SE', 1)]


def loss_grad(x, y, w):
    z0 = x @ w['w0'] + w['b0']; a0 = np.maximum(z0, 0)
    z1 = a0 @ w['w1'] + w['b1']; a1 = np.maximum(z1, 0)
    logits = a1 @ w['w2'] + w['b2']
    exp = np.exp(logits - logits.max(axis=1, keepdims=True)); p = exp / exp.sum(axis=1, keepdims=True)
    loss = -np.log(np.maximum(p[np.arange(len(y)), y], 1e-12)).mean()
    p[np.arange(len(y)), y] -= 1; d = p / len(y)
    grad = {'w2': a1.T @ d, 'b2': d.sum(axis=0)}
    d = (d @ w['w2'].T) * (z1 > 0)
    grad.update(w1=a0.T @ d, b1=d.sum(axis=0))
    d = (d @ w['w1'].T) * (z0 > 0)
    grad.update(w0=x.T @ d, b0=d.sum(axis=0))
    return float(loss), grad


if __name__ == '__main__':
    data = ROOT / 'data'; data.mkdir(exist_ok=True)
    z = ZipFile(data / 'uci447.zip')
    features, quality = [], {}
    for sensor, hz in SENSORS:
        with z.open(sensor + '.txt') as f:
            a = np.loadtxt(f, dtype=np.float64)
        assert a.shape == (2205, 60*hz) and np.isfinite(a).all(), sensor
        features.append(np.stack([a.mean(1), a.std(1, ddof=0), a.min(1), a.max(1)], axis=1))
        quality[sensor] = dict(shape=list(a.shape), hz=hz, nonfinite=0)
        print(sensor, a.shape, flush=True)
    x = np.concatenate(features, axis=1)
    with z.open('profile.txt') as f:
        profile = np.loadtxt(f, dtype=np.int64)
    y = profile[:, 2]; assert set(y) == {0, 1, 2}
    rng = np.random.default_rng(20261019)
    split = {'train': [], 'validation': [], 'test': []}
    for label in range(3):
        ids = rng.permutation(np.flatnonzero(y == label)); n = len(ids)
        for key, ids_part in zip(split, np.split(ids, [int(.7*n), int(.85*n)])):
            split[key].extend(ids_part.tolist())
    split = {k: np.array(sorted(v), dtype=np.int64) for k, v in split.items()}
    assert sum(len(v) for v in split.values()) == 2205
    assert len(set(np.concatenate(list(split.values())).tolist())) == 2205
    mu = x[split['train']].mean(0); sd = x[split['train']].std(0)
    sd = np.where(sd < 1e-12, 1., sd)
    xx = ((x-mu)/sd).astype(np.float32)
    w = {}
    for i, (a, b) in enumerate(zip([68, 32, 16], [32, 16, 3])):
        w[f'w{i}'] = rng.normal(0, np.sqrt(2/a), (a,b)).astype(np.float32)
        w[f'b{i}'] = np.zeros(b, dtype=np.float32)
    m = {k: np.zeros_like(v) for k,v in w.items()}; v = {k: np.zeros_like(v) for k,v in w.items()}
    best, best_loss, patience, step, history = None, float('inf'), 0, 0, []
    for epoch in range(80):
        ids = rng.permutation(split['train'])
        for start in range(0, len(ids), 64):
            b = ids[start:start+64]; _, g = loss_grad(xx[b], y[b], w); step += 1
            for k in w:
                m[k] = .9*m[k] + .1*g[k]; v[k] = .999*v[k] + .001*g[k]**2
                w[k] -= .001*(m[k]/(1-.9**step))/(np.sqrt(v[k]/(1-.999**step)) + 1e-8)
        val = split['validation']; vl, _ = loss_grad(xx[val], y[val], w)
        history.append(dict(epoch=epoch+1, validation_cross_entropy=vl))
        if vl < best_loss - 1e-5:
            best_loss = vl; best = {k: a.copy() for k,a in w.items()}; patience = 0
        else:
            patience += 1
        if patience >= 12: break
    w = best
    out = ROOT / 'models'; out.mkdir(exist_ok=True)
    np.savez(out/'probe_a_trained_weights.npz', **w)
    export(w, out/'probe_a_trained_fp32.onnx')
    np.savez(data/'features_and_splits.npz', raw_features=x, standardized_features=xx,
             labels=y, profile=profile, mean=mu, std=sd, **split)
    fixed = split['test'][:8]
    np.savez(out/'probe_a_trained_vectors.npz', cycle_ids=fixed, input=xx[fixed],
             raw_features=x[fixed], output=forward(xx[fixed],w))
    metrics = {k: dict(cycles=len(ids), accuracy=float((forward(xx[ids],w).argmax(1)==y[ids]).mean()),
                      class_counts=np.bincount(y[ids],minlength=3).tolist(),
                      stable_flag_counts=np.bincount(profile[ids,4],minlength=2).tolist()) for k,ids in split.items()}
    report = dict(seed=20261019, epochs=len(history), max_epochs=80, batch_size=64,
                  optimizer='Adam lr=0.001', selected_by='validation cross entropy only',
                  metrics=metrics, quality=quality, history=history,
                  feature_order=[s+'_'+stat for s,hz in SENSORS for stat in ['mean','std_ddof0','min','max']],
                  temporal_policy='Each full 60s cycle is one example. Statistics at native sensor rates; no interpolation or sample-level alignment.',
                  stability_policy='Retain all cycles, flag 0 stable / flag 1 potentially unsettled; flag is not an input feature.',
                  generalization_limit='Random disjoint cycle split; adjacent cycles and condition regimes may remain correlated. No cross-machine or robot generalization claim.',
                  npu_latency='not measured', npu_execution=False)
    (out/'training_metrics.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(metrics,indent=2))
