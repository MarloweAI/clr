#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#define H(x) do{auto e=(x);if(e!=hipSuccess){std::fprintf(stderr,"%s:%d %s: %s\n",__FILE__,__LINE__,#x,hipGetErrorString(e));std::exit(2);}}while(0)
__global__ void delayed_reset(unsigned* value){if(threadIdx.x)return;auto start=clock64();while(clock64()-start<20000000ull){};atomicExch(value,0u);}
__global__ void increment(unsigned* value){if(threadIdx.x==0)atomicAdd(value,1u);}
int main(){
 H(hipSetDevice(0));unsigned* value;H(hipMalloc(&value,sizeof(*value)));
 hipStream_t launch;H(hipStreamCreateWithFlags(&launch,hipStreamNonBlocking));
 hipGraph_t graph;H(hipGraphCreate(&graph,0));
 for(unsigned length:{8,16,9,12}){hipGraphNode_t prev=nullptr;
  for(unsigned k=0;k<length;++k){hipKernelNodeParams p{};void* args[]={&value};p.func=reinterpret_cast<void*>(increment);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;hipGraphNode_t node;H(hipGraphAddKernelNode(&node,graph,prev?&prev:nullptr,prev?1:0,&p));prev=node;}
 }
 hipGraphExec_t exec;H(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
 std::puts("prefix,iteration,at_stream_sync,after_drain,correct");
 for(unsigned sync:{0u,1u})for(unsigned iteration=0;iteration<4;++iteration){
  H(hipMemset(value,0,sizeof(*value)));H(hipDeviceSynchronize());
  delayed_reset<<<1,64,0,launch>>>(value);H(hipGetLastError());
  if(sync)H(hipStreamSynchronize(launch));
  H(hipGraphLaunch(exec,launch));H(hipStreamSynchronize(launch));
  unsigned observed=0,drained=0;H(hipMemcpy(&observed,value,sizeof(observed),hipMemcpyDeviceToHost));
  H(hipDeviceSynchronize());H(hipMemcpy(&drained,value,sizeof(drained),hipMemcpyDeviceToHost));
  std::printf("%s,%u,%u,%u,%u\n",sync?"synchronized":"async",iteration,observed,drained,unsigned(observed==45&&drained==45));std::fflush(stdout);
 }
 H(hipGraphExecDestroy(exec));H(hipGraphDestroy(graph));H(hipStreamDestroy(launch));H(hipFree(value));
}
