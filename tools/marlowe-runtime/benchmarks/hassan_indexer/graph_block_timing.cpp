#include <hip/hip_runtime.h>
#include <dlfcn.h>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
#define H(x) do {auto hip_checked_result=(x);if(hip_checked_result!=hipSuccess){fprintf(stderr,"line%d %s: %s\n",__LINE__,#x,hipGetErrorString(hip_checked_result));exit(2);}}while(0)
#define R(x) do {if(!(x)){fprintf(stderr,"line%d failed %s\n",__LINE__,#x);exit(3);}}while(0)
using Words=std::array<uint64_t,26>;
using Snapshot=uint64_t(*)(uint64_t,uint64_t,uint64_t*,uint64_t);
Snapshot snapshot;
Words get(uint64_t graph=UINT64_MAX,uint64_t block=UINT64_MAX){Words w{};R(snapshot(graph,block,w.data(),w.size())==w.size());return w;}
__global__ void count_work(int* counts,int index,unsigned long long ticks){
 auto t=wall_clock64();while(wall_clock64()-t<ticks){}
 if(threadIdx.x==0)atomicAdd(counts+index,1);
}
struct Graph {
 hipGraph_t g{};hipGraphExec_t e{};hipGraphNode_t nodes[2]{};int* data;
 int index[2]={0,1};unsigned long long delay[2];
 Graph(int* d,unsigned long long fast,unsigned long long slow):data(d),delay{fast,slow}{
  H(hipGraphCreate(&g,0));for(int i=0;i<2;++i){void* args[]={&data,&index[i],&delay[i]};auto p=params(i,args);H(hipGraphAddKernelNode(&nodes[i],g,nullptr,0,&p));}
  H(hipGraphInstantiate(&e,g,nullptr,nullptr,0));
 }
 hipKernelNodeParams params(int i,void** args){hipKernelNodeParams p{};p.func=(void*)count_work;p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;return p;}
 void change(unsigned long long ticks,bool bad=false){delay[1]=ticks;void* args[]={&data,&index[1],&delay[1]};auto p=params(1,args);if(bad)p.blockDim=dim3(0);auto err=hipGraphExecKernelNodeSetParams(e,nodes[1],&p);if(bad){R(err!=hipSuccess);hipGetLastError();}else H(err);}
 void destroy(){H(hipGraphExecDestroy(e));e=nullptr;}
 ~Graph(){if(e)destroy();H(hipGraphDestroy(g));}
};
int main(int argc,char**argv){
 R(argc==2);snapshot=reinterpret_cast<Snapshot>(dlsym(RTLD_DEFAULT,"marlowe_hip_graph_block_snapshot"));R(snapshot);
 H(hipSetDevice(0));auto header=get();const bool enabled=header[1];const int size=header[2];R(size>=1&&size<=64);
 int rate;H(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));R(rate>0);
 hipStream_t streams[2];for(auto& s:streams)H(hipStreamCreateWithFlags(&s,hipStreamNonBlocking));
 int* data;H(hipMalloc(&data,2*sizeof(int)));H(hipMemset(data,0,2*sizeof(int)));
 int expected[2]={0,0};int values[2];
 auto check=[&](){H(hipMemcpy(values,data,sizeof(values),hipMemcpyDeviceToHost));R(values[0]==expected[0]&&values[1]==expected[1]);};
 auto run=[&](Graph& g,int n,int stream=0,bool fast=true,bool destroy=false){
  hipEvent_t a,b;H(hipEventCreate(&a));H(hipEventCreate(&b));H(hipEventRecord(a,streams[stream]));
  for(int j=0;j<n;++j){H(hipGraphLaunch(g.e,streams[stream]));expected[0]+=fast;expected[1]++;}
  if(destroy)g.destroy();H(hipEventRecord(b,streams[stream]));H(hipEventSynchronize(b));
  float ms;H(hipEventElapsedTime(&ms,a,b));H(hipEventDestroy(a));H(hipEventDestroy(b));check();return double(ms)*1000;
 };
 std::puts("phase,launches,external_gpu_us,valid_records,invalid_records,partial_records,correct");
 auto report=[&](const char* phase,double us){uint64_t valid=0,invalid=0,partial=0;auto h=get();
  for(uint64_t i=0;i<h[3]&&i<h[5];++i){auto g=get(i);for(uint64_t j=0;j<g[5];++j){auto w=get(i,j);valid+=w[24];invalid+=bool(w[21]);partial+=w[9]<w[8];}}
  printf("%s,%d,%.6f,%llu,%llu,%llu,1\n",phase,expected[1],us,(unsigned long long)valid,(unsigned long long)invalid,(unsigned long long)partial);fflush(stdout);
 };
 if(std::atoi(argv[1])==0){
  Graph g(data,static_cast<unsigned long long>(rate)*20/1000,static_cast<unsigned long long>(rate)*120/1000);
  double us=run(g,3*size);report("three_blocks",us);
  if(enabled){auto meta=get(0);R(meta[5]==3);double span=0;for(int j=0;j<3;++j){auto w=get(0,j);R(w[24]&&w[9]==uint64_t(size));span+=double(w[14]-w[13])/1000;}
   R(span>3*size*100.0);R(span<us+50);}
  if(size>1){run(g,size-1);auto before=enabled?get(0)[5]:0;g.change(static_cast<unsigned long long>(rate)*160/1000);us=run(g,size);report("parameter_invalidation",us);
   if(enabled){R(get(0,before-1)[21]&2);R(!get(0,before-1)[24]);R(get(0,before)[24]);}
   run(g,size-1);before=enabled?get(0)[5]:0;us=run(g,size+1,1);report("stream_invalidation",us);
   if(enabled){R(get(0,before-1)[21]&2);R(get(0,before)[24]);}
   run(g,size-1,1);before=enabled?get(0)[5]:0;g.change(static_cast<unsigned long long>(rate)*160/1000,true);us=run(g,size,1);report("failed_setter",us);
   if(enabled){R(get(0,before-1)[21]&2);R(get(0,before)[24]);}
  }
  H(hipGraphNodeSetEnabled(g.e,g.nodes[0],0));us=run(g,size,1,false);report("disabled_root",us);
  us=run(g,size,1,false,true);report("destroy_before_sync",us);
  if(enabled){auto m=get(0);R(m[3]==1);auto w=get(0,m[5]-1);R(w[24]&&!w[25]);R(get(0,0)[24]);}
  // A distinct executable destroyed with an unfinished block cannot yield a sample.
  if(size>1){Graph partial(data,0,0);run(partial,size-1,0,true,true);if(enabled){auto m=get(1);R(m[3]&&m[5]==1);R((get(1,0)[21]&64)&&!get(1,0)[24]);}report("partial_destroy",0);}
 }else{
  {Graph g(data,0,0);run(g,size*260);if(enabled){auto m=get(0);R(m[5]==256&&m[6]==uint64_t(size*4));for(int j=0;j<256;++j)R(get(0,j)[24]);}report("record_exhaustion",0);}
  for(int i=0;i<70;++i){Graph g(data,0,0);run(g,size,0,true,true);}
  if(enabled)R(get()[5]==71);report("graph_exhaustion",0);
 }
 for(auto s:streams)H(hipStreamDestroy(s));H(hipFree(data));
}
