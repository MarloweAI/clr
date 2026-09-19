#!/usr/bin/env python3
"""Single-GPU Q/K extraction; reuse Hassan's exact scheduler and dispatch contract."""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule', choices=('serial', 'events'), required=True)
    p.add_argument('--identity', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--round', type=int, required=True)
    p.add_argument('--trials', type=int, default=8)
    p.add_argument('--iterations', type=int, default=200)
    p.add_argument('--warmup', type=int, default=40)
    a = p.parse_args()
    assert min(a.trials, a.iterations, a.warmup) > 0
    a.output.mkdir(exist_ok=False)
    root = Path(__file__).resolve().parent
    prov = json.loads((root/'provenance.json').read_text())
    assert sha(root/'indexer_projection_schedule.py') == prov['scheduler_sha256']
    assert sha(root/'projection-dispatch.json') == prov['projection_dispatch_sha256']
    expected = json.loads(a.identity.read_text())
    actual_controls = {k:os.environ.get(k) for k in expected['controls']}
    assert actual_controls == expected['controls'], actual_controls
    import torch
    import aiter.tuned_gemm as tg
    import aiter.ops.flydsl.gemm_kernels as gk
    from indexer_projection_schedule import IndexerProjectionSchedule
    assert torch.cuda.device_count() == 1
    assert torch.cuda.get_device_properties(0).gcnArchName.startswith('gfx950')
    torch.cuda.init()
    def capture_libraries(filename):
        maps = Path('/proc/self/maps').read_text()
        (a.output/filename).write_text(maps)
        result = {}
        for stem, digest in expected['libraries'].items():
            paths = {Path(line.split()[-1]).resolve() for line in maps.splitlines() if stem+'.so' in line}
            assert len(paths) == 1, (stem, paths)
            path = paths.pop()
            assert sha(path) == digest, (stem, path, sha(path), digest)
            result[stem] = dict(path=str(path), sha256=digest)
        return result
    libraries = capture_libraries('maps-before.txt')
    contract = json.loads((root/'projection-dispatch.json').read_text())
    configs = {}
    for shape in ((4,4096,2048), (4,128,6144)):
        config = tg.get_GEMM_A16W16_config(*shape,False,'torch.bfloat16','torch.bfloat16',False,False)
        assert config == contract[str(shape)]['config'], (shape, config)
        configs[str(shape)] = config
    # CPU RNG makes the same input bytes across runtimes and CUDA RNG versions.
    gen = torch.Generator(device='cpu').manual_seed(20260918)
    def tensor(shape):
        cpu = torch.randn(shape, generator=gen, dtype=torch.float32).to(torch.bfloat16)
        return cpu.to('cuda'), hashlib.sha256(cpu.view(torch.uint8).numpy().tobytes()).hexdigest()
    qx,qxh = tensor((4,2048)); qw,qwh = tensor((4096,2048))
    kx,kxh = tensor((4,6144)); kw,kwh = tensor((128,6144))
    q0, k0 = qx.clone(), kx.clone()
    for shape,x,w in [((4,4096,2048),qx,qw),((4,128,6144),kx,kw)]:
        spec = contract[str(shape)]
        assert list(x.stride()) == spec['input_stride'] and list(w.stride()) == spec['weight_stride']
        assert str(x.dtype) == spec['input_dtype'] and str(w.dtype) == spec['weight_dtype']
    identity = dict(pid=os.getpid(),schedule=a.schedule,round=a.round, libraries=libraries,
                    controls=actual_controls,torch=torch.__version__,hip=torch.version.hip,
                    configs=configs, data_sha256=dict(qx=qxh,qw=qwh,kx=kxh,kw=kwh),
                    sources={str(f):sha(f) for f in (Path(tg.__file__),Path(gk.__file__))},
                    provenance=prov)
    (a.output/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    schedule = IndexerProjectionSchedule(a.schedule, (0,))
    def projection(x):
        return tg.gemm_a16w16(x, kw), None
    def pair():
        schedule.begin(0, kx)
        q = tg.gemm_a16w16(qx, qw)
        k = schedule.key(0, projection, kx)
        return q,k
    # Warm both individual kernels before any capture or measurements.
    for _ in range(3): pair()
    torch.cuda.synchronize()
    @dataclass(frozen=True)
    class Shape:
        size: int = 1
        stream_idx: object = None
        variant_label: object = None
    shape = Shape()
    schedule.prepare_capture(shape)
    graph = torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):
        graph_outputs = pair()
    schedule.finish_capture(shape)
    checks = []
    def validate(outputs, submission, factor, kind="single"):
        for label,y,x,w,cap,maxcap in [('q',outputs[0],qx,qw,.0067,.20),('k',outputs[1],kx,kw,.012,.15)]:
            assert list(y.shape) == [4,w.shape[0]] and y.dtype == torch.bfloat16
            ref = x.float() @ w.float().T
            err = y.float()-ref
            scale = ref.square().mean().sqrt().item()
            nrms = err.square().mean().sqrt().item()/scale
            nmax = err.abs().max().item()/scale
            finite = bool(torch.isfinite(y).all().item())
            checks.append(dict(submission=submission,factor=factor,projection=label,kind=kind,
                               iterations=a.iterations if kind=='burst' else 1,nrms=nrms,nmax=nmax,
                               rms_cap=cap,max_cap=maxcap,finite=finite))
            assert finite and nrms <= cap and nmax <= maxcap, checks[-1]
    # Changed inputs are written on the launch stream, then consumed by the pair.
    # A missing entry dependency or join can expose stale/wrong outputs here.
    for submission in ('eager','graph'):
        for factor in (1.,-.5,.75,-1.):
            qx.copy_(q0*factor); kx.copy_(k0*factor)
            if submission == 'graph': graph.replay(); outputs = graph_outputs
            else: outputs = pair()
            torch.cuda.current_stream().synchronize()
            validate(outputs,submission,factor)
    for submission in ('eager','graph'):
        qx.copy_(q0*.25); kx.copy_(k0*.25)
        for _ in range(a.iterations):
            if submission == 'graph': graph.replay(); outputs = graph_outputs
            else: outputs = pair()
        torch.cuda.current_stream().synchronize()
        validate(outputs,submission,.25,kind='burst')
    qx.copy_(q0); kx.copy_(k0); torch.cuda.synchronize()
    assert capture_libraries('maps-after-warmup.txt') == libraries
    (a.output/'correctness.json').write_text(json.dumps(checks,indent=2)+'\n')
    rows = []
    submissions = ('eager','graph') if a.round%2 == 0 else ('graph','eager')
    with (a.output/'timings.jsonl').open('x') as f:
        for submission in submissions:
            operation = graph.replay if submission == 'graph' else pair
            for _ in range(a.warmup): operation()
            torch.cuda.synchronize()
            start,end = torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
            for trial in range(a.trials):
                torch.cuda.synchronize()
                start.record()
                t0 = time.perf_counter_ns()
                for _ in range(a.iterations): outputs = operation()
                t1 = time.perf_counter_ns()
                end.record(); end.synchronize()
                t2 = time.perf_counter_ns()
                row = dict(schedule=a.schedule,round=a.round,submission=submission,trial=trial,
                           iterations=a.iterations,gpu_us=start.elapsed_time(end)*1000/a.iterations,
                           host_us=(t2-t0)/1000/a.iterations,submit_us=(t1-t0)/1000/a.iterations)
                assert min(row[k] for k in ('gpu_us','host_us','submit_us')) > 0
                f.write(json.dumps(row)+'\n'); f.flush(); rows.append(row)
            print(json.dumps(dict(event='TIMED',submission=submission,rows=a.trials)),flush=True)
    assert capture_libraries('maps-after-timing.txt') == libraries
    schedule.close()
    (a.output/'COMPLETE').write_text(json.dumps(dict(rows=len(rows),checks=len(checks)))+'\n')


if __name__ == '__main__':
    main()
