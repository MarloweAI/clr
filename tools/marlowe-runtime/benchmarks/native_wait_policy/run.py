"""Fixed microbenchmark matrix, fresh processes, actual mapped-library receipts."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

SOURCE = Path(__file__).resolve().parent
CONFIGS = ('balanced-long', 'uneven-long', 'balanced-16', 'uneven-16',
           'balanced-64', 'uneven-64', 'occupied')
SCHEDULES = ('same_stream', 'side_wait')
SPECS = {
    'minimal': ('minimal_wait.cpp', [], ('block', 'case')),
    'attention': ('../attention_stream_chains/stream_chains.cpp', None,
                  ('config', 'branches', 'schedule', 'trial')),
    'dispatch': ('dispatch_holdout_extended.cpp', ['8'],
                 ('submission', 'kernels', 'delay_us', 'schedule', 'trial')),
    'late': ('late_checkpoint.cpp', ['8'], ('kernels', 'tail', 'schedule', 'trial')),
    'markers': ('marker_interleave.cpp', ['8'],
                ('submission', 'kernels', 'delay_us', 'schedule', 'trial')),
    'host': ('host_launch_overhead.cpp', ['100000'], ('profiled', 'kernels', 'trial')),
}
METRICS = ('gpu_us', 'total_us', 'host_us', 'submit_us', 'producer_us')
COMPONENTS = ('resume_gap_us', 'join_gap_sum_us', 'branch_start_skew_sum_us',
              'continuation_gap_sum_us', 'branch_span_sum_us')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_cells(case):
    if case == 'minimal':
        return Counter({(str(b), c): 8 for b in range(5)
                        for c in ('alone', 'pending_wait', 'ready_wait')})
    if case == 'attention':
        cells = ((c, b, s, t) for c in CONFIGS for b in (2, 4)
                 for s in ('serial', 'parallel', 'wide') for t in range(16))
    elif case == 'late':
        cells = ((n, tail, s, t) for n in (384, 512, 1024, 2048)
                 for tail in (4, 16, 64) for s in SCHEDULES for t in range(8))
    elif case == 'host':
        cells = ((p, 100000, t) for p in (0, 1) for t in range(3))
    else:
        lengths = (32, 128, 256, 384, 512, 768, 2048, 4096) if case == 'dispatch' else (32, 300, 512, 1024)
        delays = (0, 1000, 2500, 2950, 3050, 3150) if case == 'dispatch' else (0, 50, 200, 1000, 3000)
        delayed_n = 2048 if case == 'dispatch' else 1024
        cells = ((submission, n, d, s, t) for submission in ('graph', 'eager')
                 for n in lengths for d in delays if d == 0 or n == delayed_n
                 for s in SCHEDULES for t in range(8))
    return Counter(tuple(map(str, cell)) for cell in cells)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-lib', type=Path, required=True)
    parser.add_argument('--hsa-lib', type=Path, help='Defaults to candidate-lib')
    parser.add_argument('--stock-lib', type=Path, default=Path('/opt/rocm/lib'))
    parser.add_argument('--hipcc', default='/opt/rocm/bin/hipcc')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--queue-cap', type=int, choices=(1, 4), default=4)
    parser.add_argument('--cases', nargs='+', choices=tuple(SPECS), default=list(SPECS))
    args = parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID') or args.rounds < 3:
        parser.error('Run in an allocated single-GPU job with at least three rounds')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    candidate = args.candidate_lib.resolve()
    stock = args.stock_lib.resolve()
    hsa = (args.hsa_lib or candidate).resolve()
    libraries = {
        'stock': {'libamdhip64': stock / 'libamdhip64.so', 'libhsa-runtime64': stock / 'libhsa-runtime64.so'},
        'off': {'libamdhip64': candidate / 'libamdhip64.so', 'libhsa-runtime64': hsa / 'libhsa-runtime64.so'},
    }
    libraries['on'] = libraries['off']
    identities = {mode: {stem: sha(path) for stem, path in libs.items()}
                  for mode, libs in libraries.items()}
    manifest = {'job': os.environ['SLURM_JOB_ID'], 'node': os.uname().nodename,
                'arguments': {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                'runtime_sha256': identities, 'source_sha256': {}, 'binary_sha256': {},
                'runs': [], 'complete': False}
    records = []

    def save():
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

    try:
        for case in args.cases:
            source = (SOURCE / SPECS[case][0]).resolve()
            manifest['source_sha256'][case] = sha(source)
            with (out / f'build-{case}.log').open('w') as log:
                subprocess.run([args.hipcc, '-O3', '-std=c++17', '--offload-arch=gfx950',
                                str(source), '-o', str(out / case)], stdout=log,
                               stderr=subprocess.STDOUT, check=True)
            manifest['binary_sha256'][case] = sha(out / case)
        refs = out / 'references'
        refs.mkdir()
        save()
        for round_index in range(args.rounds):
            order = (('stock', 'off', 'on'), ('off', 'on', 'stock'), ('on', 'stock', 'off'))[round_index % 3]
            for mode in order:
                env = dict(os.environ)
                for key in ('ASC_CONFIG', 'GPU_NATIVE_EVENT_TRACE', 'MARLOWE_WAIT_DW6',
                            'MARLOWE_WAIT_MIN_DISPATCHES', 'LD_DEBUG'):
                    env.pop(key, None)
                env.update(GPU_NATIVE_EVENT_WAIT=str(int(mode == 'on')),
                           GPU_MAX_HW_QUEUES=str(args.queue_cap), ASC_RUNTIME_MODE=mode,
                           MARKER_COUNT='1024', LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so',
                           LD_LIBRARY_PATH=str(stock) if mode == 'stock' else f'{candidate}:{hsa}:{stock}')
                for case in args.cases:
                    name = f'r{round_index}-{mode}-{case}'
                    command_args = ['16', str(refs), '0'] if case == 'attention' else SPECS[case][1]
                    start = time.monotonic()
                    with (out / f'{name}.csv').open('w') as stdout, (out / f'{name}.log').open('w') as stderr:
                        result = subprocess.run([str(out / case)] + command_args, env=env,
                                                stdout=stdout, stderr=stderr, timeout=600)
                    run = {'name': name, 'round': round_index, 'mode': mode, 'case': case,
                           'exit_code': result.returncode, 'elapsed_s': time.monotonic() - start}
                    manifest['runs'].append(run)
                    save()
                    if result.returncode:
                        raise RuntimeError(f'{name}: process exit {result.returncode}')
                    log = (out / f'{name}.log').read_text()
                    mapped = {}
                    for stem, digest in identities[mode].items():
                        paths = {Path(line.split()[-1]) for line in log.splitlines()
                                 if line.startswith('LIBRARY ') and stem in line}
                        assert len(paths) == 1, (name, stem, paths)
                        path = paths.pop()
                        assert sha(path) == digest, (name, path)
                        mapped[stem] = {'path': str(path), 'sha256': digest}
                    rows = list(csv.DictReader((out / f'{name}.csv').open()))
                    assert all(row['correct'] == '1' for row in rows), name
                    keys = SPECS[case][2]
                    assert Counter(tuple(row[key] for key in keys) for row in rows) == expected_cells(case), name
                    if case == 'minimal':
                        assert sum(row['case'] == 'pending_wait' and row['pending'] == '1' for row in rows) == 40
                    run.update(rows=len(rows), mapped=mapped)
                    groups = defaultdict(list)
                    cell_keys = tuple(k for k in keys if k not in ('trial', 'block'))
                    for row in rows:
                        groups[tuple(row[k] for k in cell_keys)].append(row)
                    for cell, values in groups.items():
                        metrics = {key: statistics.median(float(row[key]) for row in values)
                                   for key in METRICS if key in values[0]}
                        assert all(math.isfinite(float(row[key])) and float(row[key]) > 0
                                   for row in values for key in metrics), (name, cell)
                        components = {key: statistics.median(float(row[key]) for row in values)
                                      for key in COMPONENTS if key in values[0]}
                        assert all(math.isfinite(float(row[key])) and float(row[key]) >= 0
                                   for row in values for key in components), (name, cell)
                        pending = sum(int(row['pending']) for row in values) if 'pending' in values[0] else None
                        records.append({'round': round_index, 'mode': mode, 'case': case,
                                        'cell': cell, 'n': len(values), 'metrics': metrics,
                                        'components': components, 'pending_count': pending,
                                        'pending_fraction': pending / len(values) if pending is not None else None})
                    save()
                    print(name, 'PASS', len(rows), flush=True)
        lookup = {(r['round'], r['mode'], r['case'], r['cell']): r for r in records}
        comparisons = defaultdict(list)
        component_comparisons = []
        for r in records:
            for control in ('stock', 'off'):
                if r['mode'] == control or r['mode'] == 'stock':
                    continue
                baseline = lookup[r['round'], control, r['case'], r['cell']]
                for metric, value in r['metrics'].items():
                    comparisons[r['mode'], control, r['case'], r['cell'], metric].append(
                        100 * (value / baseline['metrics'][metric] - 1))
                for metric, value in r['components'].items():
                    reference = baseline['components'][metric]
                    component_comparisons.append({'round': r['round'], 'mode': r['mode'],
                                                 'control': control, 'case': r['case'], 'cell': r['cell'],
                                                 'metric': metric, 'delta_us': value - reference,
                                                 'delta_pct': 100 * (value / reference - 1) if reference else None})
        summary = [{'mode': k[0], 'control': k[1], 'case': k[2], 'cell': k[3], 'metric': k[4],
                    'deltas_pct': deltas, 'repeatable_over_2pct': min(deltas) > 2}
                   for k, deltas in comparisons.items()]
        (out / 'summary.json').write_text(json.dumps({'records': records, 'comparisons': summary, 'component_comparisons': component_comparisons}, indent=2) + '\n')
        wait_improvement = []
        if 'minimal' in args.cases:
            for round_index in range(args.rounds):
                def latency(mode, cell):
                    return lookup[round_index, mode, 'minimal', (cell,)]['metrics']['gpu_us']
                on_overhead = latency('on', 'pending_wait') - latency('on', 'alone')
                for control in ('stock', 'off'):
                    baseline_overhead = latency(control, 'pending_wait') - latency(control, 'alone')
                    wait_improvement.append({'round': round_index, 'control': control,
                                             'baseline_overhead_us': baseline_overhead,
                                             'on_overhead_us': on_overhead,
                                             'passed': baseline_overhead > 0 and
                                             on_overhead < baseline_overhead * 0.5 and
                                             latency('on', 'pending_wait') < latency(control, 'pending_wait')})
        manifest.update(complete=True, reference_sha256={p.name: sha(p) for p in refs.glob('*.bin')},
                        wait_improvement=wait_improvement,
                        improvement_gate_passed=all(r['passed'] for r in wait_improvement) if wait_improvement else None,
                        performance_screen_passed=not any(r['repeatable_over_2pct'] for r in summary))
        save()
        (out / 'COMPLETE').write_text('CORRECTNESS PASS; see manifest and summary for performance\n')
        print('Performance screen passed:', manifest['performance_screen_passed'])
        # A failed performance gate remains a failed command, with all raw results retained.
        return 0 if manifest['performance_screen_passed'] and manifest['improvement_gate_passed'] is not False else 3
    except Exception as error:
        manifest['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
