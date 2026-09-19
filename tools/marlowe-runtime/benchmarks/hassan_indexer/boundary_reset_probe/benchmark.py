#!/usr/bin/env python3
"""Exact captured Q/K packets, privately replayed; not a production runtime."""
import argparse,ctypes as C,hashlib,json,os,struct,time
from pathlib import Path
from dataclasses import dataclass
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
class Metrics(C.Structure):
 _fields_=[(k,C.c_double) for k in ['prepare_us','publish_us','total_us','latency_us','dispatch_envelope_us']]+[(k,C.c_uint64) for k in ['system_hz','first0','last0','first1','last1','queue0','queue1','completed_signals']]
assert C.sizeof(Metrics)==104

def main():
 p=argparse.ArgumentParser();p.add_argument('--group',type=int,choices=[1,50],required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--units',type=int,default=200);p.add_argument('--pilot',action='store_true');a=p.parse_args()
 spec=json.loads((R/'protocol.json').read_text());out=a.out;out.mkdir(exist_ok=False);g=a.group;units=a.units
 for k,v in spec['controls'].items():assert os.environ.get(k)==v,(k,os.environ.get(k),v)
 def maps(name):
  raw=Path('/proc/self/maps').read_text();(out/name).write_text(raw);got={}
  for stem,h in spec['libraries'].items():
   paths={Path(x.split()[-1]).resolve() for x in raw.splitlines() if stem+'.so' in x};assert len(paths)==1,(stem,paths)
   q=paths.pop();assert sha(q)==h;got[stem]=dict(path=str(q),sha256=h)
  return got
 libraries=maps('maps-before-import.txt')
 for mod,h in spec['external_sources'].items():assert sha(mod)==h,mod
 import torch
 import aiter.tuned_gemm as tg
 from indexer_projection_schedule import IndexerProjectionSchedule
 torch.set_num_threads(4);assert torch.cuda.device_count()==1;torch.cuda.init()
 props=torch.cuda.get_device_properties(0);assert props.gcnArchName.startswith('gfx950') and props.multi_processor_count==256
 dispatch=json.loads((R/'projection-dispatch.json').read_text())
 for shape in [(4,4096,2048),(4,128,6144)]:assert tg.get_GEMM_A16W16_config(*shape,False,'torch.bfloat16','torch.bfloat16',False,False)==dispatch[str(shape)]['config']
 gen=torch.Generator(device='cpu').manual_seed(20260918);data={};cpu={}
 def tensor(name,shape):
  t=torch.randn(shape,generator=gen,dtype=torch.float32).to(torch.bfloat16);cpu[name]=t;data[name]=hashlib.sha256(t.view(torch.uint8).numpy().tobytes()).hexdigest();return t.cuda()
 qx=tensor('qx',(4,2048));qw=tensor('qw',(4096,2048));kx=tensor('kx',(4,6144));kw=tensor('kw',(128,6144))
 assert data==spec['data_sha256']
 refs={'q':cpu['qx'].float()@cpu['qw'].float().T,'k':cpu['kx'].float()@cpu['kw'].float().T}
 schedule=IndexerProjectionSchedule('events',(0,))
 def pair():
  schedule.begin(0,kx);yq=tg.gemm_a16w16(qx,qw);yk=schedule.key(0,lambda x:(tg.gemm_a16w16(x,kw),None),kx);return [('q',yq),('k',yk)]
 for _ in range(3):pair()
 torch.cuda.synchronize();stream=torch.cuda.Stream()
 with torch.cuda.stream(stream):
  for _ in range(3):pair()
 torch.cuda.synchronize()
 @dataclass(frozen=True)
 class Shape:
  size:int=1
  stream_idx:object=None
  variant_label:object=None
 schedule.prepare_capture(Shape());graph=torch.cuda.CUDAGraph(keep_graph=True);outputs=[]
 with torch.cuda.graph(graph,stream=stream):
  for _ in range(g):outputs.extend(pair())
 schedule.finish_capture(Shape());graph.instantiate();graph.replay();torch.cuda.synchronize()
 hip=C.CDLL(libraries['libamdhip64']['path']);hip.hipGraphDebugDotPrint.argtypes=[C.c_void_p,C.c_char_p,C.c_uint];hip.hipGraphDebugDotPrint.restype=C.c_int
 assert hip.hipGraphDebugDotPrint(graph.raw_cuda_graph(),os.fsencode(out/'graph.dot'),1)==0
 dot=(out/'graph.dot').read_text();assert 'FillFunctor' not in dot and dot.count('KERNEL\n')==2*g
 assert dot.count('(64,4,1),(128,1,1)')==g and dot.count('(2,12,1),(128,1,1)')==g
 bridge=C.CDLL(str(a.build/'extract.so'));bridge.extract_packets.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p];bridge.extract_packets.restype=C.c_int
 bridge.hip_replay_loop.argtypes=[C.c_void_p,C.c_void_p,C.c_uint];bridge.hip_replay_loop.restype=C.c_int
 raw=(C.c_ubyte*(128*g))();deps=(C.c_uint*(6*g))();sizes=(C.c_uint*(2*g))()
 assert bridge.extract_packets(graph.raw_cuda_graph_exec(),2*g,raw,deps,sizes)==0
 original=bytes(raw);(out/'captured.bin').write_bytes(original)
 # Packet grid sizes are global work-items; DOT prints workgroup counts.
 nodes=[];layers=[];remaining=set(range(2*g));previous=set();ordered=[]
 for layer in range(g):
  ready=[i for i in sorted(remaining) if set(deps[3*i+1:3*i+1+deps[3*i]])==previous]
  assert len(ready)==2,(layer,ready);bylane={}
  for i in ready:
   b=original[64*i:64*(i+1)];header,setup,wx,wy,wz,_=struct.unpack_from('<6H',b);gx,gy,gz,private,lds=struct.unpack_from('<5I',b,12);obj,karg=struct.unpack_from('<2Q',b,32)
   assert (header&255)==2 and ((header>>8)&1)==1 and ((header>>9)&3)==1 and ((header>>11)&3)==1
   assert (wx,wy,wz)==(128,1,1) and private==0 and lds==61440 and obj and karg
   label='q' if (gx,gy,gz)==(8192,4,1) else 'k' if (gx,gy,gz)==(256,12,1) else None
   assert label and label not in bylane,(i,(gx,gy,gz));bylane[label]=i
   nodes.append(dict(index=i,layer=layer,label=label,dependencies=sorted(previous),header=header,setup=setup,workgroup=[wx,wy,wz],grid=[gx,gy,gz],private=private,lds=lds,kernel_object=obj,kernarg_address=karg,kernarg_size=int(sizes[i])))
  assert set(bylane)=={'q','k'};indices=[bylane['q'],bylane['k']];ordered.extend(indices);layers.append(indices);remaining.difference_update(ready);previous=set(ready)
 assert not remaining
 templates=b''.join(original[64*i:64*(i+1)] for i in ordered);(out/'templates.bin').write_bytes(templates);write(out/'topology.json',dict(nodes=nodes,layers=layers,ordered=ordered))
 hip.hipMemcpy.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_int];hip.hipMemcpy.restype=C.c_int
 def arguments():
  result={}
  for node in nodes:
   buf=(C.c_ubyte*node['kernarg_size'])();assert hip.hipMemcpy(buf,node['kernarg_address'],len(buf),2)==0
   result[str(node['index'])]=hashlib.sha256(bytes(buf)).hexdigest()
  return result
 args_before=arguments();write(out/'kernargs-before.json',args_before)
 replay=C.CDLL(str(a.build/'replay.so'));replay.replay_create.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.POINTER(C.c_void_p)];replay.replay_create.restype=C.c_int
 replay.replay_run.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.POINTER(Metrics),C.c_void_p];replay.replay_run.restype=C.c_int
 replay.replay_dump.argtypes=[C.c_void_p,C.c_char_p];replay.replay_dump.restype=C.c_int
 replay.replay_destroy.argtypes=[C.c_void_p];replay.replay_destroy.restype=C.c_int
 template_buf=C.create_string_buffer(templates);state=C.c_void_p();assert replay.replay_create(template_buf,g,units,C.byref(state))==0
 assert replay.replay_dump(state,os.fsencode(out))==0
 checks=[];rows=[];traces=[]
 def validate(phase,factor=1.):
  for i,(label,y) in enumerate(outputs):
   actual=y.cpu().float();ref=refs[label]*factor;err=actual-ref;scale=ref.square().mean().sqrt().item();nrms=err.square().mean().sqrt().item()/scale;nmax=err.abs().max().item()/scale
   finite=bool(torch.isfinite(actual).all());assert finite and nrms<=(.0067 if label=='q' else .012) and nmax<=(.20 if label=='q' else .15),(phase,i,label,nrms,nmax)
   checks.append(dict(phase=phase,index=i,label=label,factor=factor,nrms=nrms,nmax=nmax,finite=finite))
 def rawrun(mode,profile,first):
  metric=Metrics();times=(C.c_uint64*(4*units))();assert replay.replay_run(state,mode,profile,first,C.byref(metric),times)==0
  return {k:getattr(metric,k) for k,_ in Metrics._fields_},list(times)
 validate('initial')
 for mode in [0,1,2,3,4]:
  # Poison every output, then change BOTH inputs. Private queues must see it.
  qx.copy_(cpu['qx']*-.5);kx.copy_(cpu['kx']*-.5)
  for _,y in outputs:y.fill_(float('nan'))
  torch.cuda.synchronize();rawrun(mode,0,mode%2);validate('changed-m'+str(mode),-.5)
  qx.copy_(cpu['qx']);kx.copy_(cpu['kx']);torch.cuda.synchronize();rawrun(mode,0,1-mode%2);validate('restored-m'+str(mode))
 assert maps('maps-after-capture.txt')==libraries
 events=[torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)]
 cells=['hip','m0p0','m1p0','m2p0','m3p0','m4p0','m0p1','m1p1','m2p1','m3p1','m4p1'];orders=[cells,list(reversed(cells)),cells[2:]+cells[:2],list(reversed(cells[2:]+cells[:2]))]
 assert not a.pilot
 for round_id,order in enumerate(orders):
  for cell in order:
   print('START',g,round_id,cell,flush=True)
   if cell=='hip':
    torch.cuda.synchronize();assert bridge.hip_replay_loop(graph.raw_cuda_graph_exec(),torch.cuda.current_stream().cuda_stream,units//g)==0;torch.cuda.synchronize()
   else:rawrun(int(cell[1]),int(cell[3]),round_id%2)
   for trial in range(1 if a.pilot else 8):
    if cell=='hip':
     torch.cuda.synchronize();events[0].record();t0=time.perf_counter_ns();assert bridge.hip_replay_loop(graph.raw_cuda_graph_exec(),torch.cuda.current_stream().cuda_stream,units//g)==0;t1=time.perf_counter_ns();events[1].record();events[1].synchronize();t2=time.perf_counter_ns()
     metric=dict(gpu_us=events[0].elapsed_time(events[1])*1000,host_us=(t2-t0)/1000,submit_us=(t1-t0)/1000)
    else:
     metric,ts=rawrun(int(cell[1]),int(cell[3]),(round_id+trial)%2)
     if int(cell[3]):traces.append(dict(round=round_id,cell=cell,trial=trial,times=ts))
    rows.append(dict(group=g,round=round_id,cell=cell,trial=trial,units=units,**metric))
   validate(f'r{round_id}-{cell}');write(out/'timings.json',rows);write(out/'correctness.json',checks);write(out/'dispatch-times.json',traces)
   print('PASS',g,round_id,cell,flush=True)
 assert arguments()==args_before
 assert maps('maps-after.txt')==libraries
 assert replay.replay_destroy(state)==0
 # Graph, all argument pools, tensors, and code modules remained alive through destroy.
 schedule.close()
 write(out/'identity.json',dict(group=g,units=units,pilot=a.pilot,controls=spec['controls'],libraries=libraries,data_sha256=data,device=str(props),capture_stream=int(stream.cuda_stream),side_stream=int(schedule.stream.cuda_stream),external_sources=spec['external_sources'],torch=torch.__version__,orders=orders,helpers={x:sha(a.build/x) for x in ['extract.so','replay.so']}))
 (out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
