"""Audit the fixed full matrix; report process medians and independently checked timelines.

Usage: python3 analyze_attention_stream_chains.py RESULT_DIRECTORY
No measured sample is excluded. Trace runs and geometry pilots are separate inputs.
"""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math
import re
import statistics as stats
import sys

CONFIGS = {
    'balanced-long': (128, 16384, 1), 'uneven-long': (128, 16384, 1),
    'balanced-16': (128, 16384, 16), 'uneven-16': (128, 16384, 16),
    'balanced-64': (128, 16384, 64), 'uneven-64': (128, 16384, 64),
    'occupied': (2048, 4096, 1),
}
SCHEDULES = ('serial', 'parallel', 'wide')
METRICS = ('total_us', 'host_us', 'branch_span_sum_us', 'branch_union_sum_us',
           'overlap_saved_us', 'join_gap_sum_us', 'join_span_sum_us',
           'branch_start_skew_sum_us', 'continuation_gap_sum_us')
HIP = {'stock': 'f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac',
       'off': '102086f70978c776e89e4fc0cea16b6e0afea39d24ea9c95b6c7ab1c0e492cdd',
       'on': '102086f70978c776e89e4fc0cea16b6e0afea39d24ea9c95b6c7ab1c0e492cdd'}
HSA = 'b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(root):
    m = json.loads((root / 'manifest.json').read_text())
    assert m['complete'] and (root / 'COMPLETE').read_text().strip() == 'PASS'
    assert (m['rounds'], m['repeats'], m['quick']) == (3, 16, 0)
    assert m['node'] == 'marlowe-mi355x-2'
    assert m['mode_orders'] == [['stock', 'off', 'on'], ['off', 'on', 'stock'], ['on', 'stock', 'off']]
    assert len(m['runs']) == 9
    assert {(r['round'], r['mode']) for r in m['runs']} == {(i, mode) for i in range(3) for mode in HIP}
    assert sha(root / 'benchmark') == (root / 'binary.sha256').read_text().strip()
    expected_refs = {f'ref-h{h}-t{t}-st{st}-s{s}.bin' for h, t, st in CONFIGS.values() for s in (1, 2)}
    assert set(m['reference_sha256']) == expected_refs
    for name, digest in m['reference_sha256'].items():
        assert sha(root / 'references' / name) == digest
    env = json.loads((root / 'environment.json').read_text())
    assert env.get('ASC_CONFIG') is None
    records, allrows, hardware, timelines = [], [], [], []
    for run in m['runs']:
        assert run['name'] == f"r{run['round']}-{run['mode']}" and run['returncode'] == 0
        assert run['mapped']['libamdhip64']['sha256'] == HIP[run['mode']]
        assert run['mapped']['libhsa-runtime64']['sha256'] == HSA
        log = (root / (run['name'] + '.log')).read_text()
        assert 'NATIVE_EVENT_PACKET' not in log and 'NATIVE_EVENT_QUEUE' not in log
        assert f"RUNTIME mode={run['mode']} native_wait={int(run['mode'] == 'on')}" in log
        for stem in ('libamdhip64', 'libhsa-runtime64'):
            paths = {line.split()[-1] for line in log.splitlines() if line.startswith('LIBRARY ') and stem in line}
            assert paths == {run['mapped'][stem]['path']}
        match = re.search(r'DEVICE CUs=(\d+) rate_khz=(\d+) registers=(\d+) shared=(\d+) max_blocks_per_CU=(\d+)', log)
        assert match
        hw = tuple(map(int, match.groups()))
        hardware.append(hw)
        scale = 1000.0 / hw[1]
        rows = list(csv.DictReader((root / (run['name'] + '.csv')).open()))
        expected_keys = {(c, b, s, t) for c in CONFIGS for b in (2, 4) for s in SCHEDULES for t in range(16)}
        assert len(rows) == run['rows'] == len(expected_keys)
        assert {(r['config'], int(r['branches']), r['schedule'], int(r['trial'])) for r in rows} == expected_keys
        for r in rows:
            assert tuple(int(r[k]) for k in ('heads', 'total_tokens', 'stages')) == CONFIGS[r['config']]
            assert int(r['seed']) == int(r['trial']) % 2 + 1
            assert r['correct'] == '1' and 0 <= float(r['max_abs_error']) <= 5e-5
            assert all(math.isfinite(float(r[k])) for k in METRICS)
            assert float(r['total_us']) > 0 and float(r['host_us']) > 0
            allrows.append(r)
        raw = {}
        for match in re.finditer(r'TIMELINE config=(\S+) branches=(\d+) schedule=(\S+) stage=(\d+) part=(\d+) begin=(\d+) end=(\d+)', log):
            c, b, s, st, part, begin, end = match.groups()
            key = c, int(b), s, int(st), int(part)
            assert key not in raw and int(end) > int(begin)
            raw[key] = (int(begin), int(end))
        assert set(raw) == {(c, b, s, st, p) for c in CONFIGS for b in (2, 4) for s in SCHEDULES for st in range(CONFIGS[c][2]) for p in range(b + 1)}
        for c in CONFIGS:
            for b in (2, 4):
                cells = {}
                for s in SCHEDULES:
                    group = [r for r in rows if r['config'] == c and int(r['branches']) == b and r['schedule'] == s]
                    cells[s] = {k: stats.median(float(r[k]) for r in group) for k in METRICS}
                    cells[s].update(n=len(group), min_total_us=min(float(r['total_us']) for r in group), max_total_us=max(float(r['total_us']) for r in group))
                    totals = dict.fromkeys(METRICS[2:], 0.0)
                    timeline, previous_end = [], None
                    for st in range(CONFIGS[c][2]):
                        spans = [raw[c, b, s, st, p] for p in range(b)]
                        join_lo, join_hi = raw[c, b, s, st, b]
                        first, last = min(x[0] for x in spans), max(x[1] for x in spans)
                        assert join_lo + 100 >= last
                        if previous_end is not None:
                            assert first + 100 >= previous_end
                            totals['continuation_gap_sum_us'] += (first - previous_end) * scale
                        if s == 'serial':
                            assert all(spans[p][0] + 100 >= spans[p - 1][1] for p in range(1, b))
                        span_sum = sum(y - x for x, y in spans)
                        totals['branch_span_sum_us'] += span_sum * scale
                        totals['branch_union_sum_us'] += (last - first) * scale
                        totals['overlap_saved_us'] += (span_sum - (last - first)) * scale
                        totals['join_gap_sum_us'] += (join_lo - last) * scale
                        totals['join_span_sum_us'] += (join_hi - join_lo) * scale
                        totals['branch_start_skew_sum_us'] += (max(x[0] for x in spans) - first) * scale
                        # Exact interval union of CTA envelopes, distinct from their enclosing window.
                        union, end = 0, 0
                        for lo, hi in sorted(spans):
                            union += max(0, hi - max(lo, end))
                            end = max(end, hi)
                        timeline.append({'stage': st,
                            'branches_us': [[(lo-first)*scale, (hi-first)*scale] for lo,hi in spans],
                            'join_us': [(join_lo-first)*scale, (join_hi-first)*scale],
                            'envelope_overlap_multiplicity_us': (span_sum-union)*scale,
                            'envelope_idle_inside_window_us': (last-first-union)*scale})
                        previous_end = join_hi
                    trial0 = next(r for r in group if r['trial'] == '0')
                    for k, value in totals.items():
                        assert abs(value - float(trial0[k])) <= .002, (run['name'], c, b, s, k, value, trial0[k])
                    timelines.append({'run': run['name'], 'config': c, 'branches': b, 'schedule': s,
                        'stages': timeline, 'stages_without_any_envelope_overlap': sum(t['envelope_overlap_multiplicity_us'] <= .01 for t in timeline)})
                records.append({'round': run['round'], 'runtime': run['mode'], 'config': c, 'branches': b,
                                'cells': cells, 'parallel_speedup': cells['serial']['total_us']/cells['parallel']['total_us']})
    assert all(h == hardware[0] for h in hardware)
    grouped = defaultdict(list)
    for r in records:
        grouped[r['config'], r['branches'], r['runtime']].append(r)
    aggregates = []
    for (c, b, mode), reps in grouped.items():
        aggregates.append({'config': c, 'branches': b, 'runtime': mode,
            'cells': {s: {k: stats.median(r['cells'][s][k] for r in reps) for k in METRICS} for s in SCHEDULES},
            'process_parallel_speedups': [r['parallel_speedup'] for r in reps]})
    comparisons = []
    for c in CONFIGS:
        for b in (2, 4):
            for rnd in range(3):
                by_mode = {r['runtime']: r for r in records if (r['config'], r['branches'], r['round']) == (c, b, rnd)}
                comparisons.append({'config': c, 'branches': b, 'round': rnd,
                    **{f'native_on_vs_off_{s}_pct': 100*(by_mode['on']['cells'][s]['total_us']/by_mode['off']['cells'][s]['total_us']-1) for s in SCHEDULES}})
    return {'complete': True, 'job': m['job'], 'node': m['node'], 'processes': 9,
        'measured_operations': len(allrows), 'checked_measured_elements': sum(int(r['heads'])*64 for r in allrows),
        'max_absolute_reference_error': max(float(r['max_abs_error']) for r in allrows),
        'checked_trial0_stage_envelopes': sum(len(t['stages'])*(t['branches']+1) for t in timelines),
        'hardware': dict(zip(('CUs', 'clock_khz', 'registers', 'shared_bytes', 'max_blocks_per_CU'), hardware[0])),
        'runs': records, 'aggregates': aggregates, 'comparisons': comparisons, 'timelines': timelines,
        'limitations': ['One allocation, three fresh processes per runtime; not independent job replication.',
            'Synthetic FP32 attention-like kernels, not production attention or full-model results.',
            'Useful KV work fixed across arities; partition reduction and launch overhead change.',
            'Stage counts change query feedback semantics; compare schedules only within a configuration.',
            'CTA envelopes establish possible overlap, not actual CU utilization or simultaneous progress.',
            'CSV branch_union_sum_us is the enclosing branch window, not interval union.',
            'CSV overlap_saved_us is summed spans minus enclosing windows, not measured time saved.',
            'Raw per-stage envelopes retained for trial0 only; all operations validate ordering in the producer.',
            'No clock locking or sample exclusions. Runtime library hashes verified at execution.']}


if __name__ == '__main__':
    print(json.dumps(analyze(Path(sys.argv[1])), indent=2))
