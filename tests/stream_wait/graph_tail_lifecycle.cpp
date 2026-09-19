#include <hip/hip_runtime.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <string>
#include <vector>
#define H(x) do { auto e=(x); if(e!=hipSuccess){std::fprintf(stderr,"%s:%d %s: %s\n",__FILE__,__LINE__,#x,hipGetErrorString(e));std::exit(2);} } while(0)
__global__ void step(unsigned* values,unsigned branch,unsigned final,unsigned epoch,unsigned long long cycles){
 if(threadIdx.x)return;auto start=clock64();while(clock64()-start<cycles){};
 atomicExch(values+branch,final?branch+1+32*epoch:0);
}
__global__ void observe(unsigned* values,unsigned width,unsigned epoch,unsigned long long* bad){
 unsigned i=threadIdx.x;if(i<width && atomicAdd(values+i,0u)!=i+1+32*epoch)atomicOr(bad,1ull<<i);
}
struct Graph {hipGraph_t graph=nullptr;std::vector<hipGraphNode_t> tails;};
Graph make_graph(unsigned* values,unsigned width,bool reverse,unsigned epoch){
 Graph g;H(hipGraphCreate(&g.graph,0));g.tails.resize(width);std::vector<unsigned> ids(width);std::iota(ids.begin(),ids.end(),0);if(reverse)std::reverse(ids.begin(),ids.end());
 for(unsigned branch:ids){hipGraphNode_t prev=nullptr;unsigned length=8+(branch*5)%9;
  for(unsigned k=0;k<length;++k){unsigned final=k+1==length;unsigned long long cycles=final?2000000ull*(1+branch%5):1000ull;
   void* args[]={&values,&branch,&final,&epoch,&cycles};hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(step);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;
   hipGraphNode_t node;H(hipGraphAddKernelNode(&node,g.graph,prev?&prev:nullptr,prev?1:0,&p));prev=node;
  }g.tails[branch]=prev;
 }return g;
}
void update_tail(hipGraphExec_t exec,hipGraphNode_t node,unsigned* values,unsigned branch,unsigned epoch,bool graph_only){
 unsigned final=1;unsigned long long cycles=2000000ull*(1+(branch+epoch)%5);void* args[]={&values,&branch,&final,&epoch,&cycles};
 hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(step);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;
 if(graph_only)H(hipGraphKernelNodeSetParams(node,&p));else H(hipGraphExecKernelNodeSetParams(exec,node,&p));
}
int main(){
 H(hipSetDevice(0));constexpr unsigned width=15;unsigned* values;unsigned long long *bad,*host;
 H(hipMalloc(&values,width*sizeof(unsigned)));H(hipMalloc(&bad,sizeof(*bad)));H(hipHostMalloc(&host,sizeof(*host)));
 hipStream_t streams[2];for(auto& s:streams)H(hipStreamCreateWithFlags(&s,hipStreamNonBlocking));
 std::puts("case,creation_order,iteration,observed_bad_mask,eventual_correct,correct");
 for(const std::string mode:{"replay","clone","kernel_update","exec_update","child","child_update"})for(unsigned order=0;order<2;++order){
  Graph original=make_graph(values,width,order,0);hipGraph_t selected=original.graph,clone=nullptr,parent=nullptr;hipGraphNode_t child=nullptr,observer=nullptr;auto tails=original.tails;
  bool ischild=mode=="child"||mode=="child_update";
  if(mode=="clone"){H(hipGraphClone(&clone,original.graph));selected=clone;for(unsigned i=0;i<width;++i)H(hipGraphNodeFindInClone(&tails[i],original.tails[i],clone));}
  if(ischild){H(hipGraphCreate(&parent,0));H(hipGraphAddChildGraphNode(&child,parent,nullptr,0,original.graph));unsigned epoch=0,n=width;void* args[]={&values,&n,&epoch,&bad};
   hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(observe);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;H(hipGraphAddKernelNode(&observer,parent,&child,1,&p));selected=parent;
  }
  hipGraphExec_t exec;H(hipGraphInstantiate(&exec,selected,nullptr,nullptr,0));
  // A cloned executable must remain usable after both source graphs are gone.
  if(mode=="clone"){H(hipGraphDestroy(clone));clone=nullptr;H(hipGraphDestroy(original.graph));original.graph=nullptr;}
  for(unsigned iteration=0;iteration<4;++iteration){unsigned epoch=(mode=="kernel_update"||mode=="exec_update"||mode=="child_update")?iteration+1:0;
   if(mode=="kernel_update")for(unsigned b=0;b<width;++b)update_tail(exec,tails[b],values,b,epoch,false);
   if(mode=="exec_update"){Graph replacement=make_graph(values,width,order,epoch);hipGraphNode_t error=nullptr;hipGraphExecUpdateResult result;H(hipGraphExecUpdate(exec,replacement.graph,&error,&result));if(result!=hipGraphExecUpdateSuccess)return 3;H(hipGraphDestroy(replacement.graph));}
   if(mode=="child_update"){
    for(unsigned b=0;b<width;++b)update_tail(nullptr,original.tails[b],values,b,epoch,true);
    H(hipGraphExecChildGraphNodeSetParams(exec,child,original.graph));unsigned n=width;void* args[]={&values,&n,&epoch,&bad};hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(observe);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;H(hipGraphExecKernelNodeSetParams(exec,observer,&p));
   }
   H(hipMemset(values,0,width*sizeof(unsigned)));H(hipMemset(bad,0,sizeof(*bad)));H(hipDeviceSynchronize());
   const unsigned stream_sequence[]={0,0,1,0};auto launch=streams[stream_sequence[iteration]];H(hipGraphLaunch(exec,launch));
   observe<<<1,64,0,launch>>>(values,width,epoch,bad);H(hipGetLastError());H(hipMemcpyAsync(host,bad,sizeof(*bad),hipMemcpyDeviceToHost,launch));H(hipStreamSynchronize(launch));auto observed=*host;
   H(hipDeviceSynchronize());std::vector<unsigned> final(width);H(hipMemcpy(final.data(),values,width*sizeof(unsigned),hipMemcpyDeviceToHost));bool eventual=true;for(unsigned i=0;i<width;++i)eventual&=final[i]==i+1+32*epoch;
   std::printf("%s,%u,%u,%llu,%u,%u\n",mode.c_str(),order,iteration,observed,unsigned(eventual),unsigned(eventual&&observed==0));std::fflush(stdout);if(!eventual||observed)return 4;
  }
  H(hipGraphExecDestroy(exec));if(parent)H(hipGraphDestroy(parent));if(clone)H(hipGraphDestroy(clone));if(original.graph)H(hipGraphDestroy(original.graph));
 }
 for(auto s:streams)H(hipStreamDestroy(s));H(hipFree(values));H(hipFree(bad));H(hipHostFree(host));return 0;
}
