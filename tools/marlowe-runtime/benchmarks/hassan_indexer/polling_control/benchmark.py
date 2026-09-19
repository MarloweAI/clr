import argparse,ctypes,hashlib,json,os,time
from pathlib import Path
from dataclasses import dataclass
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:Path(p).write_text(json.dumps(v,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--proof',action='store_true');a=p.parse_args()
 spec=json.loads((R/'spec.json').read_text());cfg=spec['cases'][a.case];controls=spec['controls']|{'GPU_STREAMOPS_CP_WAIT':str(cfg['cp'])};out=a.out;out.mkdir(exist_ok=False)
 if a.proof:controls.update(AMD_LOG_LEVEL='4',AMD_LOG_MASK='256')
 assert all(sha(R/f)==h for f,h in json.loads((R/'harness.json').read_text()).items());assert all(os.environ.get(k)==v for k,v in controls.items())
 import torch
 import aiter.tuned_gemm as tg
 from indexer_projection_schedule import IndexerProjectionSchedule
 torch.set_num_threads(4);torch.cuda.init();assert torch.cuda.device_count()==1
 assert torch.cuda.get_device_properties(0).gcnArchName.startswith('gfx950')
 def maps(name):
  text=Path('/proc/self/maps').read_text();(out/name).write_text(text);got={}
  for stem,h in spec['libraries'].items():
   paths={Path(x.split()[-1]).resolve() for x in text.splitlines() if stem+'.so' in x};assert len(paths)==1;path=paths.pop();assert sha(path)==h;got[stem]={'path':str(path),'sha256':h}
  return got
 libraries=maps('maps-before.txt');assert all(sha(f)==h for f,h in spec['external_sources'].items())
 dispatch=json.loads((R/'projection-dispatch.json').read_text())
 for shape in [(4,4096,2048),(4,128,6144)]:assert tg.get_GEMM_A16W16_config(*shape,False,'torch.bfloat16','torch.bfloat16',False,False)==dispatch[str(shape)]['config']
 gen=torch.Generator(device='cpu').manual_seed(20260918);cpu={};data={}
 def tensor(name,shape):
  x=torch.randn(shape,generator=gen,dtype=torch.float32).to(torch.bfloat16);cpu[name]=x;data[name]=hashlib.sha256(x.view(torch.uint8).numpy().tobytes()).hexdigest();return x.cuda()
 qx=tensor('qx',(4,2048));qw=tensor('qw',(4096,2048));kx=tensor('kx',(4,6144));kw=tensor('kw',(128,6144))
 refs={'q':cpu['qx'].float()@cpu['qw'].float().T,'k':cpu['kx'].float()@cpu['kw'].float().T}
 main_stream=torch.cuda.Stream();side=torch.cuda.Stream();q=lambda:tg.gemm_a16w16(qx,qw);k=lambda:tg.gemm_a16w16(kx,kw)
 schedule=IndexerProjectionSchedule('events' if cfg.get('events') else 'serial',(0,));side=schedule.stream
 def pair():
  schedule.begin(0,kx);yq=q();yk=schedule.key(0,lambda x:(tg.gemm_a16w16(x,kw),None),kx);return [('q',yq),('k',yk)]
 with torch.cuda.stream(main_stream):
  for _ in range(3):pair()
 with torch.cuda.stream(side):
  for _ in range(3):k()
 torch.cuda.synchronize()
 graphs=[];outputs=[];dot_nodes=[]
 def capture(stream,fn):
  graph=torch.cuda.CUDAGraph(keep_graph=True)
  with torch.cuda.graph(graph,stream=stream):ys=fn()
  graph.instantiate();graphs.append(graph);outputs.extend(ys);return graph
 @dataclass(frozen=True)
 class Shape:
  size:int=1
  stream_idx:object=None
  variant_label:object=None
 if cfg['mode']==0:
  schedule.prepare_capture(Shape());g=capture(main_stream,lambda:[y for _ in range(cfg['group']) for y in pair()]);schedule.finish_capture(Shape());qg=kg=None
 else:
  qg=capture(main_stream,lambda:[('q',q())]);kg=capture(side,lambda:[('k',k())]);g=None
 hip=ctypes.CDLL(libraries['libamdhip64']['path']);hip.hipGraphDebugDotPrint.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_uint]
 for i,graph in enumerate(graphs):
  path=out/f'graph-{i}.dot';assert hip.hipGraphDebugDotPrint(graph.raw_cuda_graph(),os.fsencode(path),1)==0;dot=path.read_text();assert 'FillFunctor' not in dot;dot_nodes.append({'q':dot.count('(64,4,1),(128,1,1)'),'k':dot.count('(2,12,1),(128,1,1)'),'kernels':dot.count('KERNEL\n')})
 assert sum(x['q'] for x in dot_nodes)==sum(x['k'] for x in dot_nodes)==cfg['group'];assert sum(x['kernels'] for x in dot_nodes)==2*cfg['group']
 helper=ctypes.CDLL(str(R/'launcher.so'));ptr=ctypes.c_void_p;helper.setup.argtypes=[ctypes.POINTER(ptr),ptr,ptr];helper.launch.argtypes=[ptr,ptr,ptr,ptr,ctypes.c_int,ctypes.c_int];helper.inspect.argtypes=[ptr,ctypes.POINTER(ctypes.c_uint32)];helper.cleanup.argtypes=[ptr]
 state=ptr();assert helper.setup(ctypes.byref(state),main_stream.cuda_stream,side.cuda_stream)==0
 raw=lambda graph:graph.raw_cuda_graph_exec() if graph else None
 def run(n):assert helper.launch(state,raw(g),raw(qg),raw(kg),cfg['mode'],n)==0
 checks=[]
 def check(phase,factor):
  torch.cuda.synchronize()
  for i,(label,y) in enumerate(outputs):
   ref=refs[label]*factor;actual=y.cpu().float();err=actual-ref;scale=ref.square().mean().sqrt().item();nrms=err.square().mean().sqrt().item()/scale;nmax=err.abs().max().item()/scale;finite=bool(torch.isfinite(actual).all());assert finite and nrms<=(.0067 if label=='q' else .012) and nmax<=(.20 if label=='q' else .15)
   checks.append(dict(phase=phase,index=i,label=label,nrms=nrms,nmax=nmax,finite=finite))
 # Input publication is ordered on main; the side must observe the ready edge.
 with torch.cuda.stream(main_stream):qx.copy_(qx*-.5);kx.copy_(kx*-.5)
 run(1);check('changed',-.5)
 with torch.cuda.stream(main_stream):qx.copy_(cpu['qx']);kx.copy_(cpu['kx'])
 run(1);check('initial',1)
 units=cfg['group'] if a.proof else 200;launches=units//cfg['group'];run(launches);torch.cuda.synchronize();rows=[]
 start,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
 for trial in range(1 if a.proof else 8):
  torch.cuda.synchronize();start.record(main_stream);t0=time.perf_counter_ns();run(launches);t1=time.perf_counter_ns();end.record(main_stream);end.synchronize();t2=time.perf_counter_ns();rows.append(dict(trial=trial,units=units,launches=launches,gpu_us=start.elapsed_time(end)*1000/units,submit_us=(t1-t0)/1000/units,host_us=(t2-t0)/1000/units))
 check('final',1);values=(ctypes.c_uint32*3)();assert helper.inspect(state,values)==0;values=list(values)
 assert values[0]==(2+(2 if a.proof else 9)*launches if cfg['mode'] in (2,3) else 0)
 assert values[1:]==([values[0]]*2 if cfg['mode']==3 else [0,0]);assert helper.cleanup(state)==0;assert maps('maps-after.txt')==libraries
 write(out/'identity.json',dict(case=a.case,round=a.round,proof=a.proof,config=cfg,controls=controls,libraries=libraries,helper_sha256=sha(R/'launcher.so'),external_sources=spec['external_sources'],data_sha256=data,nodes=dot_nodes,generations=values,streams=[int(main_stream.cuda_stream),int(side.cuda_stream)]));write(out/'timings.json',rows);write(out/'correctness.json',checks);schedule.close();(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
