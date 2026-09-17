#!/usr/bin/env python3
"""Summarize complete runs without filtering samples; model the dependency DAG."""
import argparse, collections, csv, json, pathlib, re, statistics

def pipeline_estimate(layers, h, c, d, streams):
    if streams == 1: return layers*(h+c+d)
    ready = {0:h}; consumed = {}; io=h; compute=0.; output=0.
    for layer in range(layers):
        if layer+1 < layers:
            io=max(io,consumed.get(layer-1,0.))+h
            ready[layer+1]=io
        compute=max(compute,ready[layer])+c
        consumed[layer]=compute
        if streams==2: io=max(io,compute)+d; output=io
        else: output=max(output,compute)+d
    return max(compute,output)

def expected(key, components):
    bench, config, schedule, submission = key
    def component(phase, path='isolated'):
        return components[(bench,config,path,phase,submission)]
    if bench=='attention_fetch':
        path,kind=schedule.split('-'); copy=component('copy',path); resident=component('resident',path)
        missed=component('miss_attention',path); merge=component('merge',path)
        return (copy+resident+missed if kind=='serial' else max(resident,copy+missed))+merge
    if bench=='pipeline':
        layers=int(re.search(r'-l(\d+)-',config)[1])
        return pipeline_estimate(layers,component('h2d'),component('compute'),component('d2h'),
                                 {'serial':1,'two_streams':2,'three_streams':3}[schedule])
    if bench=='experts':
        if schedule=='batched': return None # Different kernel geometry; no independent DAG estimate.
        stages=[component(f'expert{i}') for i in range(4)]
        streams=int(schedule[0])
        return max(sum(stages[i::streams]) for i in range(streams))+component('merge')
    if bench=='mixed':
        stages=[component('compute'),component('scan0')] if config=='matrix-kv' else [component('scan0'),component('scan1')]
        return sum(stages) if schedule=='serial' else max(stages)
    raise ValueError(key)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('directory',type=pathlib.Path); args=p.parse_args(); root=args.directory
    manifest=json.loads((root/'manifest.json').read_text()); assert manifest.get('passed'), 'incomplete measurement matrix'
    groups=collections.defaultdict(list)
    for process in manifest['processes']:
        assert process['returncode']==0
        for row in csv.DictReader((root/(process['tag']+'.csv')).open()):
            assert row['correct']=='1'
            key=(row['benchmark'],row['config'],row['schedule'],row['phase'],row['submission'],process['mode'],process['round'])
            groups[key].append(row)
    medians={k:{metric:statistics.median(float(r[metric]) for r in rows) for metric in ('gpu_us','host_us','submit_us')} for k,rows in groups.items()}
    stage_groups=collections.defaultdict(list)
    for key,metrics in medians.items():
        bench,config,schedule,phase,submission,mode,round_index=key
        if mode=='stock' and phase!='total':stage_groups[(bench,config,schedule,phase,submission)].append(metrics['gpu_us'])
    components={k:statistics.median(v) for k,v in stage_groups.items()}
    totals=sorted({(k[0],k[1],k[2],k[4]) for k in medians if k[3]=='total'})
    report=[]
    for key in totals:
        bench,config,schedule,submission=key
        row=dict(benchmark=bench,config=config,schedule=schedule,submission=submission,expected_us=expected(key,components))
        for mode in manifest['libraries']:
            r=[medians[(bench,config,schedule,'total',submission,mode,i)] for i in range(manifest['rounds'])]
            row[mode+'_us']=statistics.median(x['gpu_us'] for x in r)
            row[mode+'_rounds_us']=[x['gpu_us'] for x in r]
            row[mode+'_host_us']=statistics.median(x['host_us'] for x in r)
        for base in ('stock','off','experimental'):
            row['on_vs_'+base+'_pct']=100*(row['on_us']/row[base+'_us']-1)
        if 'revised' in manifest['libraries']:
            for base in ('stock','on','experimental'):
                row['revised_vs_'+base+'_pct']=100*(row['revised_us']/row[base+'_us']-1)
        row['on_over_expected_pct']=100*(row['on_us']/row['expected_us']-1) if row['expected_us'] else None
        report.append(row)
    out={'processes':len(manifest['processes']), 'rows':sum(len(v) for v in groups.values()),'correct':True,
         'aggregation':'median of fresh-process medians; every timing retained', 'totals':report,
         'components':[dict(zip(('benchmark','config','schedule','phase','submission'),k),stock_us=v) for k,v in components.items()]}
    (root/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    with (root/'totals.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(report[0]));writer.writeheader();writer.writerows(report)
    print(f"{out['processes']} processes; {out['rows']} timings; {len(report)} total rows")
    print('graph totals: stock / v8 off / v8 on / experimental / ideal us; v8 vs stock, experimental %')
    for row in report:
        if row['submission']!='graph': continue
        times=' / '.join(f'{row[m+"_us"]:.1f}' for m in ('stock','off','on','experimental'))
        ideal=f"{row['expected_us']:.1f}" if row['expected_us'] else 'n/a'
        print(row['benchmark'],row['config'],row['schedule'],times,'/',ideal,
              f"{row['on_vs_stock_pct']:+.1f}% {row['on_vs_experimental_pct']:+.1f}%")

if __name__=='__main__':main()
