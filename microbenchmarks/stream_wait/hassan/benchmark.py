#!/usr/bin/env python3
"""Warm Q/K graph microbenchmark using Hassan's unchanged kernels and scheduler.
The 50-pair graph is a synthetic replay-grouping control, not model serving.
"""
import argparse,ctypes,hashlib,json,os,time
from pathlib import Path
from dataclasses import dataclass
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--mode',required=True);p.add_argument('--proof',action='store_true');a=p.parse_args()
 spec=json.loads(a.spec.read_text());policy=spec['modes'][a.mode];spec=spec|policy;cfg=spec['cases'][a.case];out=a.out;out.mkdir(exist_ok=False)
 for f,h in spec['sources'].items():assert sha(R/f)==h
 for k,v in spec['controls'].items():assert os.environ.get(k)==v,(k,os.environ.get(k),v)
 import torch
 import aiter.tuned_gemm as tg
 import aiter.ops.flydsl.gemm_kernels as gk
 from indexer_projection_schedule import IndexerProjectionSchedule
 torch.set_num_threads(4);assert torch.cuda.device_count()==1;torch.cuda.init()
 props=torch.cuda.get_device_properties(0);assert props.gcnArchName.startswith('gfx950') and props.multi_processor_count==256
 def maps(name):
  raw=Path('/proc/self/maps').read_text();(out/name).write_text(raw);got={}
  for stem,h in spec['libraries'].items():
   paths={Path(x.split()[-1]).resolve() for x in raw.splitlines() if stem+'.so' in x};assert len(paths)==1
   q=paths.pop();assert sha(q)==h;got[stem]=dict(path=str(q),sha256=h)
  return got
 libraries=maps('maps-before.txt')
 for mod,h in spec['external_sources'].items():assert sha(mod)==h,mod
 dispatch=json.loads((R/'projection-dispatch.json').read_text())
 for shape in [(4,4096,2048),(4,128,6144)]:assert tg.get_GEMM_A16W16_config(*shape,False,'torch.bfloat16','torch.bfloat16',False,False)==dispatch[str(shape)]['config']
 gen=torch.Generator(device='cpu').manual_seed(20260918);data={};cpu={}
 def tensor(name,shape):
  t=torch.randn(shape,generator=gen,dtype=torch.float32).to(torch.bfloat16);cpu[name]=t;data[name]=hashlib.sha256(t.view(torch.uint8).numpy().tobytes()).hexdigest();return t.cuda()
 qx=tensor('qx',(4,2048));qw=tensor('qw',(4096,2048));kx=tensor('kx',(4,6144));kw=tensor('kw',(128,6144))
 refs={'q':cpu['qx'].float()@cpu['qw'].float().T,'k':cpu['kx'].float()@cpu['kw'].float().T}
 schedule=IndexerProjectionSchedule('events' if cfg['operation']=='events' else 'serial',(0,))
 def q():return tg.gemm_a16w16(qx,qw)
 def k():return tg.gemm_a16w16(kx,kw)
 def pair():
  schedule.begin(0,kx);yq=q();yk=schedule.key(0,lambda x:(tg.gemm_a16w16(x,kw),None),kx);return [('q',yq),('k',yk)]
 def unit():
  if cfg['operation']=='q':return [('q',q())]
  if cfg['operation']=='k':return [('k',k())]
  return pair()
 # Match the original distinction: ordinary main and side warmed before a new capture stream exists.
 for _ in range(3):pair()
 torch.cuda.synchronize()
 capture_stream=torch.cuda.Stream()
 if cfg['capture']=='warm':
  with torch.cuda.stream(capture_stream):
   for _ in range(3):unit()
  torch.cuda.synchronize()
 @dataclass(frozen=True)
 class Shape:
  size:int=1
  stream_idx:object=None
  variant_label:object=None
 schedule.prepare_capture(Shape())
 graph=torch.cuda.CUDAGraph(keep_graph=True);outputs=[]
 with torch.cuda.graph(graph,stream=capture_stream):
  for _ in range(cfg['group']):outputs.extend(unit())
 schedule.finish_capture(Shape());graph.instantiate()
 lib=ctypes.CDLL(libraries['libamdhip64']['path']);lib.hipGraphDebugDotPrint.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_uint];lib.hipGraphDebugDotPrint.restype=ctypes.c_int
 assert lib.hipGraphDebugDotPrint(graph.raw_cuda_graph(),os.fsencode(out/'graph.dot'),1)==0
 dot=(out/'graph.dot').read_text();fills=2 if cfg['capture']=='cold' else 0;units=1 if cfg['operation'] in ['q','k'] else 2
 assert dot.count('FillFunctor')==fills,(a.case,'fill count',dot.count('FillFunctor'),fills)
 assert dot.count('KERNEL\n')==units*cfg['group']+fills,(a.case,'kernel count')
 qcount=cfg['group'] if cfg['operation']!='k' else 0;kcount=cfg['group'] if cfg['operation']!='q' else 0
 assert dot.count('(64,4,1),(128,1,1)')==qcount and dot.count('(2,12,1),(128,1,1)')==kcount
 graph.replay();torch.cuda.synchronize()
 checks=[]
 def validate(phase,factor=1.):
  for i,(label,y) in enumerate(outputs):
   ref=refs[label]*factor;actual=y.cpu().float();err=actual-ref;scale=ref.square().mean().sqrt().item();nrms=err.square().mean().sqrt().item()/scale;nmax=err.abs().max().item()/scale
   finite=bool(torch.isfinite(actual).all());assert finite and nrms<=(.0067 if label=='q' else .012) and nmax<=(.20 if label=='q' else .15),(a.case,label,nrms,nmax)
   checks.append(dict(phase=phase,index=i,label=label,factor=factor,nrms=nrms,nmax=nmax,finite=finite))
 validate('initial')
 # Actual changed-input publication before the requested graph; keep checks outside timing.
 qx.copy_(qx*-.5);kx.copy_(kx*-.5);graph.replay();torch.cuda.synchronize();validate('changed',-.5)
 qx.copy_(cpu['qx']);kx.copy_(cpu['kx']);torch.cuda.synchronize()
 units_per_trial=cfg['group'] if a.proof else 200
 launches=units_per_trial//cfg['group'];assert launches*cfg['group']==units_per_trial
 for _ in range(launches):graph.replay()
 torch.cuda.synchronize();rows=[]
 start,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
 for trial in range(1 if a.proof else 8):
  torch.cuda.synchronize();start.record();t0=time.perf_counter_ns()
  for _ in range(launches):graph.replay()
  t1=time.perf_counter_ns();end.record();end.synchronize();t2=time.perf_counter_ns()
  row=dict(case=a.case,round=a.round,trial=trial,units=units_per_trial,graph_launches=launches,gpu_us=start.elapsed_time(end)*1000/units_per_trial,host_us=(t2-t0)/1000/units_per_trial,submit_us=(t1-t0)/1000/units_per_trial)
  rows.append(row)
 validate('final')
 assert maps('maps-after.txt')==libraries
 write(out/'identity.json',dict(case=a.case,mode=a.mode,proof=a.proof,round=a.round,config=cfg,controls=spec['controls'],libraries=libraries,data_sha256=data,device=str(props),capture_stream=int(capture_stream.cuda_stream),side_stream=int(schedule.stream.cuda_stream),nodes=dict(kernels=units*cfg['group']+fills,fills=fills,q=qcount,k=kcount),external_sources=spec['external_sources'],torch=torch.__version__))
 write(out/'timings.json',rows);write(out/'correctness.json',checks);schedule.close();(out/'COMPLETE').write_text('PASS\n')
 print(json.dumps(dict(case=a.case,round=a.round,rows=len(rows),checks=len(checks),nodes=units*cfg['group']+fills)),flush=True)
if __name__=='__main__':main()
