// Entry ordering across pinned copies, copy-first roots and a forwarded event.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#define H(x) do { auto e=(x); if(e!=hipSuccess){std::fprintf(stderr,"%d %s: %s\n",__LINE__,#x,hipGetErrorString(e));std::exit(2);} } while(0)
__global__ void delayed_reset(unsigned* value){if(threadIdx.x)return;auto start=clock64();while(clock64()-start<10000000ull){};atomicExch(value,0u);}
__global__ void increment_checked(unsigned* value,const unsigned* input,unsigned offset,unsigned words){if(threadIdx.x==0){bool ok=input[offset]==13u&&input[offset+words-1]==13u;atomicAdd(value,ok?1u:1000u);}}
int main(){
 H(hipSetDevice(0));unsigned *value,*host_value,*input,*host_input;
 constexpr size_t maxbytes=8u*1024u*1024u;H(hipMalloc(&value,4));H(hipHostMalloc(&host_value,4));*host_value=0;
 H(hipMalloc(&input,4*maxbytes));H(hipHostMalloc(&host_input,4*maxbytes));
 for(size_t i=0;i<maxbytes;++i)host_input[i]=13;
 hipStream_t launch,foreign;H(hipStreamCreateWithFlags(&launch,hipStreamNonBlocking));H(hipStreamCreateWithFlags(&foreign,hipStreamNonBlocking));
 hipEvent_t event;H(hipEventCreateWithFlags(&event,hipEventDisableTiming));
 std::puts("copy_roots,bytes,prefix,iteration,observed,correct");
 for(unsigned copy_roots:{0u,1u})for(size_t bytes:{size_t(8192),maxbytes}){
  unsigned words=bytes/sizeof(unsigned);hipGraph_t graph;H(hipGraphCreate(&graph,0));unsigned branch=0;
  for(unsigned length:{8u,16u,9u,12u}){
   unsigned offset=branch*words;hipGraphNode_t prev=nullptr;
   if(copy_roots)H(hipGraphAddMemcpyNode1D(&prev,graph,nullptr,0,input+offset,host_input+offset,bytes,hipMemcpyHostToDevice));
   for(unsigned k=0;k<length;++k){void* args[]={&value,&input,&offset,&words};hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(increment_checked);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;hipGraphNode_t node;H(hipGraphAddKernelNode(&node,graph,prev?&prev:nullptr,prev?1:0,&p));prev=node;}++branch;
  }
  hipGraphExec_t exec;H(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
  for(unsigned prefix:{0u,1u,2u})for(unsigned iteration=0;iteration<2;++iteration){
   H(hipMemset(value,0,4));H(hipMemset(input,0,4*bytes));H(hipDeviceSynchronize());
   auto producer=prefix==2?foreign:launch;
   delayed_reset<<<1,64,0,producer>>>(value);H(hipGetLastError());
   // Prefix1 tests an external pinned H2D frontier. Prefix2 forwards the full
   // foreign producer frontier through a launch-stream event wait.
   H(hipMemcpyAsync(input,host_input,4*bytes,hipMemcpyHostToDevice,producer));
   if(prefix==1)H(hipMemcpyAsync(value,host_value,4,hipMemcpyHostToDevice,producer));
   if(prefix==2){H(hipEventRecord(event,foreign));H(hipStreamWaitEvent(launch,event,0));}
   // Two consecutive launches exercise reuse without a host synchronization.
   H(hipGraphLaunch(exec,launch));H(hipGraphLaunch(exec,launch));
   H(hipStreamSynchronize(launch));unsigned observed;H(hipMemcpy(&observed,value,4,hipMemcpyDeviceToHost));
   std::printf("%u,%zu,%u,%u,%u,%u\n",copy_roots,bytes,prefix,iteration,observed,unsigned(observed==90));std::fflush(stdout);if(observed!=90)return 3;
  }
  H(hipGraphExecDestroy(exec));H(hipGraphDestroy(graph));
 }
 H(hipEventDestroy(event));H(hipStreamDestroy(launch));H(hipStreamDestroy(foreign));H(hipFree(value));H(hipFree(input));H(hipHostFree(host_value));H(hipHostFree(host_input));
}
