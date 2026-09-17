#!/usr/bin/env python3
"""Run a fixed, correctness-checked one-GPU matrix; retain every process/sample."""
import argparse, csv, hashlib, json, os, pathlib, re, socket, subprocess, time

CASES = ('attention_fetch', 'pipeline', 'experts', 'mixed')
MODES = ('stock', 'off', 'on', 'experimental')

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''): h.update(block)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=pathlib.Path, required=True)
    p.add_argument('--candidate-lib', type=pathlib.Path, required=True)
    p.add_argument('--experimental-lib', type=pathlib.Path, required=True)
    p.add_argument('--revised-lib', type=pathlib.Path)
    p.add_argument('--stock-lib', type=pathlib.Path, default=pathlib.Path('/opt/rocm/lib'))
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--rounds', type=int, default=3)
    p.add_argument('--trials', type=int, default=12)
    args = p.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'must run inside allocation'
    assert args.rounds >= 3 and args.trials >= 4
    args.output.mkdir(parents=True, exist_ok=False)
    refs = args.output.resolve() / 'references'; refs.mkdir()
    binary = args.binary.resolve()
    libs = {'stock': args.stock_lib.resolve(), 'off': args.candidate_lib.resolve(),
            'on': args.candidate_lib.resolve(), 'experimental': args.experimental_lib.resolve()}
    modes = MODES + (('revised',) if args.revised_lib else ())
    if args.revised_lib: libs['revised'] = args.revised_lib.resolve()
    manifest = {'started': time.time(), 'hostname': socket.gethostname(),
                'job': os.environ['SLURM_JOB_ID'], 'gpu_visible': os.getenv('ROCR_VISIBLE_DEVICES'),
                'binary': {'path': str(binary), 'sha256': digest(binary)},
                'rounds': args.rounds, 'trials': args.trials, 'processes': [],
                'sources': {str(f.name): digest(f) for f in pathlib.Path(__file__).parent.iterdir()
                            if f.suffix in ('.hpp', '.cpp', '.py')}, 'libraries': {}}
    for mode, lib in libs.items():
        manifest['libraries'][mode] = {name: {'path': str((lib/name).resolve()), 'sha256': digest(lib/name)}
                                      for name in ('libamdhip64.so', 'libhsa-runtime64.so')}
    def save():
        (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    save()
    for round_index in range(args.rounds):
        order = modes[round_index % len(modes):] + modes[:round_index % len(modes)]
        for mode in order:
            for case in CASES:
                tag = f'r{round_index}-{mode}-{case}'
                env = os.environ.copy()
                for key in list(env):
                    if key.startswith(('DEBUG_HIP_GRAPH_', 'DEBUG_HIP_NATIVE_WAIT_')) or key in (
                        'GPU_NATIVE_EVENT_WAIT', 'GPU_NATIVE_EVENT_TRACE', 'GPU_STREAMOPS_CP_WAIT',
                        'LD_PRELOAD', 'ROCP_TOOL_LIB', 'ROCPROFILER_TOOL_LIBRARIES'):
                        env.pop(key)
                env.update(LD_LIBRARY_PATH=str(libs[mode])+':'+str(args.stock_lib),
                           LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so', LLM_RUNTIME_MODE=mode,
                           GPU_NATIVE_EVENT_WAIT='1' if mode in ('on','experimental','revised') else '0',
                           GPU_MAX_HW_QUEUES='4', GPU_NATIVE_EVENT_TRACE='0', GPU_STREAMOPS_CP_WAIT='0',
                           LLM_TRIALS=str(args.trials), LLM_REFERENCE_DIR=str(refs))
                if mode == 'experimental':
                    env.update(DEBUG_HIP_GRAPH_LONG_PATH_FIRST='1', DEBUG_HIP_GRAPH_QUEUE_SPARE='1',
                               DEBUG_HIP_GRAPH_MARKER_CONTROL='1', DEBUG_HIP_NATIVE_WAIT_DIAGNOSTIC_CONTROL='1',
                               DEBUG_HIP_GRAPH_MARKER_TRACE='0')
                receipt = {'tag': tag, 'round': round_index, 'mode': mode, 'case': case, 'start':time.time(),
                           'controls': {k:v for k,v in env.items() if k.startswith(('GPU_', 'DEBUG_HIP_', 'LLM_'))}}
                manifest['processes'].append(receipt); save()
                with (args.output/(tag+'.csv')).open('w') as out, (args.output/(tag+'.log')).open('w') as err:
                    try:
                        result = subprocess.run([str(binary), case], env=env, stdout=out, stderr=err, timeout=300)
                        receipt['returncode'] = result.returncode
                    except subprocess.TimeoutExpired:
                        receipt['timeout'] = True; save(); raise
                receipt['elapsed_s'] = time.time()-receipt['start']
                save()
                assert result.returncode == 0, f'{tag}: failed; raw artifacts retained'
                rows = list(csv.DictReader((args.output/(tag+'.csv')).open()))
                assert rows and all(r['correct']=='1' for r in rows), f'{tag}: correctness'
                keys = [(r['config'],r['schedule'],r['phase'],r['submission'],r['trial']) for r in rows]
                assert len(keys)==len(set(keys)), f'{tag}: duplicate samples'
                reference_tag = f'r0-stock-{case}.csv'
                if (args.output/reference_tag).exists():
                    reference = list(csv.DictReader((args.output/reference_tag).open()))
                    expected = {(r['config'],r['schedule'],r['phase'],r['submission'],r['trial']) for r in reference}
                    assert set(keys)==expected, f'{tag}: sample coverage differs'
                log = (args.output/(tag+'.log')).read_text()
                assert 'CUs=256' in log and 'mode='+mode in log, f'{tag}: device receipt'
                mapped = sorted(set(re.findall(r'LIBRARY .*?(/\S+lib(?:amdhip64|hsa-runtime64|rocblas)\S*)', log)))
                receipt['mapped_libraries'] = {path: digest(path) for path in mapped}
                for name in ('libamdhip64', 'libhsa-runtime64'):
                    actual = {sha for path,sha in receipt['mapped_libraries'].items() if name in pathlib.Path(path).name}
                    assert actual=={manifest['libraries'][mode][name+'.so']['sha256']}, f'{tag}: library identity'
                if mode=='experimental': assert 'EXPERIMENTAL marker=2 wait=1025' in log
                receipt['rows'] = len(rows)
                receipt['csv_sha256'] = digest(args.output/(tag+'.csv'))
                save(); print(tag, 'PASS', len(rows), f"{receipt['elapsed_s']:.1f}s", flush=True)
    manifest['references'] = {f.name:digest(f) for f in refs.iterdir()}
    manifest['finished'] = time.time(); manifest['passed'] = True; save()
    print('All runtime/case processes passed', flush=True)

if __name__ == '__main__': main()
