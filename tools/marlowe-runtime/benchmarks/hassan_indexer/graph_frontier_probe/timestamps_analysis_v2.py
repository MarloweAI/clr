#!/usr/bin/env python3
"""Independent post-run audit of the preserved 55564 dispatch trace.
Segment IDs are storage indices, not topological order. Receipts are emitted in
prebuilt publication order; pair the ordinal Q and K on their respective lanes.
These data are for dispatch intervals only, never latency qualification.
"""
import argparse, hashlib, json, math, re, statistics
from pathlib import Path
from timestamps import sha, files
W=Path(__file__).resolve().parent

def analyze(log, dot, group):
    nodes={int(i):name for i,name in re.findall(r'\| \{ID \| (\d+) \| ([^\\\n]+)',dot)}
    assert len(nodes)==2*group and len(set(nodes.values()))==2
    qname,kname=nodes[0],nodes[1]
    assert all(nodes[2*i]==qname and nodes[2*i+1]==kname for i in range(group))
    edges={(int(a),int(b)) for a,b in re.findall(r'"graph_\d+_node_(\d+)" -> "graph_\d+_node_(\d+)"',dot)}
    assert edges=={(a,b) for i in range(group-1) for a in [2*i,2*i+1] for b in [2*i+2,2*i+3]}
    graphs={}
    for rec in re.findall(r'GRAPH_FRONTIER_DISPATCH [^\r\n]*',log):
        fields,name=rec.split(' kernel=',1);v=dict(re.findall(r'(\w+)=(\S+)',fields))
        assert v['valid']=='1' and v['kernels']=='1'
        v={k:(int(x) if k!='graph' else x) for k,x in v.items()}|{'kernel':name}
        assert v['end']>v['start'] and v['frequency']>0 and name in [qname,kname]
        graphs.setdefault((v['graph'],v['serial']),[]).append(v)
    count=1802 if group==1 else 38
    assert len(graphs)==count and {s for _,s in graphs}==set(range(1,count+1)) and len({g for g,_ in graphs})==1
    rows=[];orders=set();gaps=[];lanes=set()
    for (graph,serial),seq in sorted(graphs.items(),key=lambda x:x[0][1]):
        assert len(seq)==2*group and {v['segment'] for v in seq}==set(range(2*group))
        orders.add(tuple(v['segment'] for v in seq))
        freq={v['frequency'] for v in seq};assert len(freq)==1;scale=1e6/freq.pop()
        q=[v for v in seq if v['kernel']==qname];k=[v for v in seq if v['kernel']==kname]
        assert len(q)==len(k)==group
        qp={v['physical'] for v in q};kp={v['physical'] for v in k}
        assert len(qp)==len(kp)==1 and qp!=kp;lanes.update(qp|kp)
        # The frozen DOT has a complete join between each pair. The launch
        # builder walks dependency levels, and receipts retain publication order.
        assert seq==[v for pair in zip(q,k) for v in pair]
        prev_end=None
        for i,(a,b) in enumerate(zip(q,k)):
            start=min(a['start'],b['start']);end=max(a['end'],b['end'])
            if prev_end is not None:assert start>=prev_end;gaps.append((start-prev_end)*scale)
            prev_end=end
            rows.append(dict(graph=graph,serial=serial,pair=i,segments=[a['segment'],b['segment']],physical=[a['physical'],b['physical']],start=start,end=end,frequency=a['frequency'],q_us=(a['end']-a['start'])*scale,k_us=(b['end']-b['start'])*scale,span_us=(end-start)*scale,overlap_us=max(0,min(a['end'],b['end'])-max(a['start'],b['start']))*scale,start_skew_us=(b['start']-a['start'])*scale))
    assert len(orders)==1 and len(lanes)==2
    def summary(rr):
        return dict(pairs=len(rr),overlap_pairs=sum(v['overlap_us']>0 for v in rr),**{f:statistics.median(v[f] for v in rr) for f in ['q_us','k_us','span_us','overlap_us','start_skew_us']})
    timed_start=3+200//group
    return dict(graphs=len(graphs),physical_queues=len(lanes),segment_publication_order=list(next(iter(orders))),all_launches=summary(rows),post_warmup=summary([v for v in rows if v['serial']>=timed_start]),intragraph_gap_us_median=statistics.median(gaps) if gaps else None),rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.input;m=json.loads((root/'manifest.json').read_text())
    assert m['job']=='55564' and m['revision']=='v4' and m['complete'] is False
    assert m['build']==json.loads((W/'runtime-build-v4.json').read_text())
    for f,h in m['sources'].items():assert sha(W/f)==h
    assert [v['case'] for v in m['runs']]==['events-g1','events-g50']
    spec=json.loads((root/'spec.json').read_text());out=dict(job=m['job'],runtime=m['build']['libraries'],original_job_status='FAILED: analyzer assumed adjacent numeric segment IDs form pairs',original_manifest_sha256=sha(root/'manifest.json'),analysis_source_sha256=sha(Path(__file__)),timing_eligible=False,qualified=False,cases={})
    for v in m['runs']:
        case=v['case'];d=root/case;group=spec['cases'][case]['group']
        assert v['returncode']==0 and v['files']==files(d) and v['log_sha256']==sha(root/(case+'.log')) and (d/'COMPLETE').read_text()=='PASS\n'
        ident=json.loads((d/'identity.json').read_text());assert ident['controls']==spec['modes']['local']['controls'] and ident['controls']['GPU_GRAPH_DIAGNOSTIC_FRONTIER_TIMESTAMPS']=='1' and ident['controls']['GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE']=='0'
        assert {k+'.so':x['sha256'] for k,x in ident['libraries'].items()}==m['build']['libraries']
        for f in ['maps-before.txt','maps-after.txt']:
            raw=(d/f).read_text()
            for stem,x in ident['libraries'].items():assert {l.split()[-1] for l in raw.splitlines() if stem+'.so' in l}=={x['path']}
        checks=json.loads((d/'correctness.json').read_text());assert {(x['phase'],x['index']) for x in checks}=={(p,i) for p in ['initial','changed','final'] for i in range(2*group)}
        assert all(x['finite'] and math.isfinite(x['nrms']) and x['nrms']<=(.0067 if x['label']=='q' else .012) and x['nmax']<=(.20 if x['label']=='q' else .15) for x in checks)
        summary,rows=analyze((root/(case+'.log')).read_text(),(d/'graph.dot').read_text(),group)
        out['cases'][case]=dict(summary=summary,rows=rows,log_sha256=v['log_sha256'],correctness_checks=len(checks))
    out['audit_passed']=True
    if a.output.exists():assert json.loads(a.output.read_text())==out
    else:a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='cases'}|{'cases':{k:v['summary'] for k,v in out['cases'].items()}},indent=2))
if __name__=='__main__':main()
