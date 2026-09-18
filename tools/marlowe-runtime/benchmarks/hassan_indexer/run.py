#!/usr/bin/env python3
"""Run a frozen stock/current × serial/events matrix and retain every trial."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')


def audit(specpath, out):
    spec=json.loads(specpath.read_text()); manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['spec_sha256']==sha(specpath)
    assert len(manifest['processes'])==sum(map(len,spec['orders']))
    root=Path(__file__).resolve().parent
    for name,digest in spec['sources'].items(): assert sha(root/name)==digest,name
    perround={}; data=None; external=None; checked=0
    expected_steps=[(r,mode) for r,order in enumerate(spec['orders']) for mode in order]
    for rec,step in zip(manifest['processes'],expected_steps):
        r,mode=step; policy=spec['modes'][mode]
        assert (rec['round'],rec['mode'])==step and rec['returncode']==0
        path=out/rec['directory']
        for name,digest in rec['artifacts'].items(): assert sha(path/name)==digest,name
        ident=json.loads((path/'identity.json').read_text())
        assert ident['schedule']==policy['schedule'] and ident['round']==r
        assert ident['controls']==policy['controls']
        assert {k:v['sha256'] for k,v in ident['libraries'].items()}==policy['libraries']
        assert ident['configs']=={k:v['config'] for k,v in json.loads((root/'projection-dispatch.json').read_text()).items()}
        if data is None: data=ident['data_sha256']; external=ident['sources']
        assert ident['data_sha256']==data and ident['sources']==external
        for p,digest in spec['external_sources'].items(): assert ident['sources'][p]==digest
        checks=json.loads((path/'correctness.json').read_text())
        assert len(checks)==20
        assert {(c['submission'],c['factor'],c['projection'],c['kind']) for c in checks}==({
            (s,f,k,'single') for s in ('eager','graph') for f in (1.,-.5,.75,-1.) for k in ('q','k')} | {
            (s,.25,k,'burst') for s in ('eager','graph') for k in ('q','k')})
        for c in checks:
            assert c['iterations']==(spec['iterations'] if c['kind']=='burst' else 1)
            assert c['finite'] and c['nrms']<=c['rms_cap'] and c['nmax']<=c['max_cap']
        checked+=len(checks)
        rows=[json.loads(line) for line in (path/'timings.jsonl').read_text().splitlines()]
        assert len(rows)==2*spec['trials']
        assert {(x['submission'],x['trial']) for x in rows}=={
            (s,t) for s in ('eager','graph') for t in range(spec['trials'])}
        for x in rows:
            assert x['schedule']==policy['schedule'] and x['round']==r and x['iterations']==spec['iterations']
            assert all(0<x[f]<1e9 for f in ('gpu_us','host_us','submit_us'))
        for submission in ('eager','graph'):
            perround[r,mode,submission]={f:statistics.median(x[f] for x in rows if x['submission']==submission)
                                        for f in ('gpu_us','host_us','submit_us')}
    summary={'passed':True,'processes':len(expected_steps),'rows':len(expected_steps)*2*spec['trials'],
             'correctness_rows':checked,'qualified_for_production':False,'workload':'Hassan Q/K single-GPU extraction',
             'spec_sha256':sha(specpath),'submissions':{}}
    pairs=[('current_serial','stock_serial'),('current_events','stock_events'),
           ('stock_events','stock_serial'),('current_events','current_serial')]
    for submission in ('eager','graph'):
        med={mode:{f:statistics.median(perround[r,mode,submission][f] for r in range(len(spec['orders'])))
                   for f in ('gpu_us','host_us','submit_us')} for mode in spec['modes']}
        contrasts={}
        for a,b in pairs:
            contrasts[a+'/'+b]={f:{'delta_us':med[a][f]-med[b][f], 'percent':100*(med[a][f]/med[b][f]-1),
                                  'round_percent':[100*(perround[r,a,submission][f]/perround[r,b,submission][f]-1)
                                                   for r in range(len(spec['orders']))]} for f in med[a]}
        contrasts['interaction']={f:(med['current_events'][f]-med['current_serial'][f])-
                                    (med['stock_events'][f]-med['stock_serial'][f]) for f in med['stock_serial']}
        summary['submissions'][submission]=dict(median_us=med,contrasts=contrasts)
    graph = summary['submissions']['graph']['contrasts']
    summary['performance_screen'] = {
        'scope':'Graph current/stock for serial and events; GPU and host; all rounds and aggregate',
        'maximum_regression_percent':2,
        'passed':all(graph[pair][field]['percent']<=2 and all(x<=2 for x in graph[pair][field]['round_percent'])
                     for pair in ('current_serial/stock_serial','current_events/stock_events')
                     for field in ('gpu_us','host_us'))}
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--audit',action='store_true');a=p.parse_args()
    if a.audit:
        result=audit(a.spec,a.out)
        assert result==json.loads((a.out/'summary.json').read_text())
        print(json.dumps({k:v for k,v in result.items() if k!='submissions'}));return
    spec=json.loads(a.spec.read_text());root=Path(__file__).resolve().parent
    for name,digest in spec['sources'].items(): assert sha(root/name)==digest,name
    a.out.mkdir(exist_ok=False)
    manifest=dict(spec_sha256=sha(a.spec),processes=[],started=time.time(),job_id=os.environ.get('SLURM_JOB_ID'))
    write(a.out/'manifest.json',manifest)
    for r,order in enumerate(spec['orders']):
        for mode in order:
            policy=spec['modes'][mode]
            ident=a.out/f'identity-{mode}.json'
            write(ident,dict(controls=policy['controls'],libraries=policy['libraries']))
            env={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_'))
                 and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','LD_DEBUG')}
            env.update(policy['controls'],LD_LIBRARY_PATH=policy['lib']+':/opt/rocm/lib',
                       LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so')
            directory=f'r{r}-{mode}'
            rec=dict(round=r,mode=mode,directory=directory,started=time.time())
            manifest['processes'].append(rec);write(a.out/'manifest.json',manifest)
            print(json.dumps(dict(event='START',round=r,mode=mode)),flush=True)
            cmd=[sys.executable,str(root/'benchmark.py'),'--schedule',policy['schedule'],
                 '--identity',str(ident.resolve()),'--output',str((a.out/directory).resolve()),
                 '--round',str(r),'--trials',str(spec['trials']),'--iterations',str(spec['iterations']),
                 '--warmup',str(spec['warmup'])]
            with (a.out/f'{directory}.log').open('x') as log:
                ret=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
            rec.update(returncode=ret.returncode,elapsed_s=time.time()-rec['started'])
            if ret.returncode==0:
                rec['artifacts']={p.name:sha(p) for p in (a.out/directory).iterdir() if p.is_file()}
                assert 'COMPLETE' in rec['artifacts']
            write(a.out/'manifest.json',manifest)
            assert ret.returncode==0, f'{directory} failed; preserved log'
            print(json.dumps(dict(event='FINISHED',round=r,mode=mode)),flush=True)
    result=audit(a.spec,a.out);write(a.out/'summary.json',result)
    (a.out/'COMPLETE').write_text('All processes, rows, correctness and library/source identities audited.\n')
    print(json.dumps({k:v for k,v in result.items() if k!='submissions'}),flush=True)


if __name__=='__main__': main()
