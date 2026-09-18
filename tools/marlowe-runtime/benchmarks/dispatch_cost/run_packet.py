"""Same-byte packet controls on unchanged attention fixtures and original waiter.

Timing and trace processes are separate. No subprocess timeout cancels workloads;
the enclosing Slurm watcher provides soft inspection deadlines.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

import run as dispatch
import run_arrival as arrival

MODES = ('stock', 'off', 'guarded', 'prior_relaxed', 'relaxed', 'poll1',
         'poll16', 'ordered', 'zero', 'ordered_zero')
TRACES = ('guarded', 'relaxed', 'poll1', 'poll16', 'ordered', 'zero', 'ordered_zero')
BENCHES = ('dispatch', 'arrival', 'waiter')
MODULES = {'dispatch': dispatch, 'arrival': arrival}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def controls(mode, trace=False, cap=4):
    return {
        'GPU_NATIVE_EVENT_WAIT': str(int(mode not in ('stock', 'off'))),
        'GPU_NATIVE_EVENT_DIAGNOSTIC_RELAX_COST': str(int(mode not in ('stock', 'off', 'guarded'))),
        'GPU_NATIVE_EVENT_DIAGNOSTIC_MIN_DISPATCHES': '256',
        'GPU_NATIVE_EVENT_DIAGNOSTIC_POLL_INTERVAL': '1' if mode == 'poll1' else '16' if mode == 'poll16' else '4',
        'GPU_NATIVE_EVENT_DIAGNOSTIC_ORDER_PREWAIT': str(int(mode in ('ordered', 'ordered_zero'))),
        'GPU_NATIVE_EVENT_DIAGNOSTIC_ZERO_TARGET': str(int(mode in ('zero', 'ordered_zero'))),
        'GPU_NATIVE_EVENT_TRACE': str(int(trace)),
        'GPU_MAX_HW_QUEUES': str(cap),
    }


def audit_run(out, run, expected_hashes, repeats):
    bench, name = run['bench'], run['name']
    libs = {k: Path(v['path']) for k, v in run['mapped'].items()} if 'mapped' in run else run['libraries']
    if bench in MODULES:
        rows, mapped, log = MODULES[bench].audit_process(out, name, libs, repeats, run['controls'])
    else:
        log = (out / f'{name}.log').read_text()
        mapped = {}
        for stem in ('libamdhip64', 'libhsa-runtime64'):
            paths = {Path(line.split()[-1]) for line in log.splitlines()
                     if line.startswith('LIBRARY ') and stem in line}
            assert len(paths) == 1, (name, stem, paths)
            path = paths.pop()
            mapped[stem] = {'path': str(path), 'sha256': sha(path)}
        with (out / f'{name}.csv').open() as f:
            rows = list(csv.DictReader(f))
        assert Counter((r['block'], r['case']) for r in rows) == Counter(
            {(str(b), c): 8 for b in range(5) for c in ('alone', 'pending_wait', 'ready_wait')})
        assert all(r['correct'] == '1' and math.isfinite(float(r['gpu_us'])) and float(r['gpu_us']) > 0 for r in rows)
        assert all(r['pending'] == '1' for r in rows if r['case'] == 'pending_wait')
    for stem, record in mapped.items():
        assert record['sha256'] == expected_hashes[stem], (name, stem, record)
    reasons = Counter()
    if not run['timing_eligible']:
        for line in log.splitlines():
            if not line.startswith('NATIVE_COST '):
                continue
            rec = dict(re.findall(r'(\w+)=([^ ]+)', line))
            reasons[rec['reason']] += 1
            for field, key in (
                ('minimum', 'MIN_DISPATCHES'), ('relaxed', 'RELAX_COST'),
                ('interval', 'POLL_INTERVAL'), ('ordered', 'ORDER_PREWAIT'),
                ('zero_target', 'ZERO_TARGET'),
            ):
                assert rec[field] == run['controls']['GPU_NATIVE_EVENT_DIAGNOSTIC_' + key], (name, field, rec)
            if rec['reason'] == 'emit':
                assert rec['producer'] != rec['consumer'] and rec['producer'] != str(2**64 - 1)
                assert int(rec['generation']) > 0
        assert reasons, (name, 'missing compiled control receipts')
        if run['controls']['GPU_MAX_HW_QUEUES'] == '1':
            assert reasons['emit'] == 0
    return rows, mapped, dict(reasons)


def audit(out):
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['complete'] and manifest['rounds'] == 3 and manifest['repeats'] == 8
    assert len(manifest['runs']) == 3 * len(MODES) * len(BENCHES) + len(TRACES) * len(BENCHES) + 2
    for bench, rec in manifest['sources'].items():
        assert sha(rec['path']) == rec['sha256']
        assert sha(out / bench) == manifest['binary_sha256'][bench]
    for run in manifest['runs']:
        assert run['returncode'] == 0
        rows, mapped, reasons = audit_run(out, run, manifest['runtime_hashes'][run['mode']],
                                         8 if run['timing_eligible'] else 1)
        assert len(rows) == run['rows'] and mapped == run['mapped']
        if not run['timing_eligible']:
            assert reasons == run['admission_reasons']
    for filename, digest in manifest['reference_sha256'].items():
        assert sha(out / 'references' / filename) == digest
    assert len(manifest['calibration_sha256']) == 14
    for filename, digest in manifest['calibration_sha256'].items():
        assert sha(out / 'references' / filename) == digest
    assert (out / 'COMPLETE').read_text() == 'PASS\n'
    rec = {'passed': True, 'job': manifest['job'], 'processes': len(manifest['runs']),
           'timing_rows': sum(r['rows'] for r in manifest['runs'] if r['timing_eligible']),
           'trace_rows': sum(r['rows'] for r in manifest['runs'] if not r['timing_eligible']),
           'hip_sha256': manifest['runtime_hashes']['relaxed']['libamdhip64']}
    (out / 'audit.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(rec), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--candidate-lib', type=Path)
    p.add_argument('--prior-lib', type=Path)
    p.add_argument('--waiter-source', type=Path)
    p.add_argument('--audit-only', action='store_true')
    args = p.parse_args()
    out = args.output.resolve()
    if args.audit_only:
        audit(out)
        return
    assert os.environ.get('SLURM_JOB_ID') and args.candidate_lib and args.prior_lib and args.waiter_source
    out.mkdir(parents=True, exist_ok=False)
    refs = out / 'references'
    refs.mkdir()
    root = Path(__file__).resolve().parent
    sources = {'dispatch': root / 'attention_dispatch.cpp', 'arrival': root / 'attention_arrival.cpp',
               'waiter': args.waiter_source.resolve()}
    paths = {mode: Path('/opt/rocm/lib') if mode == 'stock' else args.prior_lib.resolve()
             if mode == 'prior_relaxed' else args.candidate_lib.resolve() for mode in MODES}
    libraries = {mode: {stem: path / (stem + '.so') for stem in ('libamdhip64', 'libhsa-runtime64')}
                 for mode, path in paths.items()}
    manifest = {'job': os.environ['SLURM_JOB_ID'], 'node': os.uname().nodename,
                'sources': {k: {'path': str(v), 'sha256': sha(v)} for k, v in sources.items()},
                'runtime_hashes': {m: {s: sha(v) for s, v in ll.items()} for m, ll in libraries.items()},
                'rounds': 3, 'repeats': 8, 'runs': [], 'complete': False, 'binary_sha256': {}}
    def save():
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    save()
    for bench, source in sources.items():
        with (out / f'{bench}-build.log').open('w') as log:
            subprocess.run(['/opt/rocm/bin/hipcc', '-O3', '-std=c++17', '--offload-arch=gfx950',
                            str(source), '-o', str(out / bench)], stdout=log, stderr=subprocess.STDOUT, check=True)
        manifest['binary_sha256'][bench] = sha(out / bench)
        save()
    aggregate = []
    def execute(bench, name, mode, trace=False, cap=4):
        ctrl = controls(mode, trace, cap)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('GPU_NATIVE_EVENT_', 'GPU_GRAPH_DIAGNOSTIC_'))
               and k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_DEBUG')}
        env.update(ctrl, ARRIVAL_CALIBRATE='1' if name == 'arrival-r0-stock' else '0',
                   LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so', LD_LIBRARY_PATH=f'{paths[mode]}:/opt/rocm/lib')
        run = {'bench': bench, 'name': name, 'mode': mode, 'controls': ctrl,
               'timing_eligible': not trace, 'started': time.time()}
        manifest['runs'].append(run)
        save()
        argv = [str(out / bench)] + ([str(1 if trace else 8), str(refs)] if bench != 'waiter' else [])
        with (out / f'{name}.csv').open('w') as stdout, (out / f'{name}.log').open('w') as stderr:
            result = subprocess.run(argv, env=env, stdout=stdout, stderr=stderr)
        run.update(returncode=result.returncode, elapsed_s=time.time() - run['started'])
        save()
        assert result.returncode == 0, (name, result.returncode)
        rows, mapped, reasons = audit_run(out, dict(run, libraries=libraries[mode]),
                                         manifest['runtime_hashes'][mode], 1 if trace else 8)
        run.update(rows=len(rows), mapped=mapped)
        if trace:
            run['admission_reasons'] = reasons
        save()
        print(name, 'PASS', len(rows), 'rows', flush=True)
        return rows
    for rnd in range(3):
        order = MODES[rnd * 3 % len(MODES):] + MODES[:rnd * 3 % len(MODES)]
        for mode in order:
            for bench in BENCHES:
                rows = execute(bench, f'{bench}-r{rnd}-{mode}', mode)
                groups = defaultdict(list)
                keys = MODULES[bench].KEYS[:-1] if bench in MODULES else ('case',)
                fields = MODULES[bench].FIELDS if bench in MODULES else ('gpu_us',)
                for row in rows:
                    groups[tuple(row[k] for k in keys)].append(row)
                for cell, group in groups.items():
                    aggregate.append({'round': rnd, 'mode': mode, 'bench': bench, 'cell': cell,
                                      'n': len(group), 'metrics': {f: statistics.median(float(row[f]) for row in group) for f in fields}})
                (out / 'summary.json').write_text(json.dumps(aggregate, indent=2) + '\n')
    for mode in TRACES:
        for bench in BENCHES:
            execute(bench, f'{bench}-trace-{mode}', mode, trace=True)
    for bench in ('dispatch', 'arrival'):
        execute(bench, f'{bench}-trace-ordered-q1', 'ordered', trace=True, cap=1)
    manifest.update(complete=True, reference_sha256={p.name: sha(p) for p in refs.glob('*.bin')},
                    calibration_sha256={p.name: sha(p) for p in refs.glob('delay-*.txt')})
    save()
    (out / 'COMPLETE').write_text('PASS\n')
    audit(out)


if __name__ == '__main__':
    main()
