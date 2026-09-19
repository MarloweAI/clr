#include <hip/hip_runtime.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <random>
#include <vector>
#include <string>
#include <unistd.h>

#define HIP(call) do { hipError_t err=(call); if(err!=hipSuccess) { std::fprintf(stderr,"%s:%d %s: %s\n",__FILE__,__LINE__,#call,hipGetErrorString(err)); std::exit(2); } } while(0)

// Timer work only widens the completion-order observation window. This fixture
// tests a public graph/stream ordering guarantee; it reports no performance score.
__global__ void terminal_step(unsigned* values,unsigned branch,unsigned final_step,
                              unsigned long long cycles) {
  if(threadIdx.x!=0)return;
  const auto start=clock64();
  while(clock64()-start<cycles) {}
  atomicExch(values+branch,final_step?branch+1:0);
}
__global__ void observe_completion(unsigned* values,unsigned width,unsigned long long* bad) {
  unsigned i=threadIdx.x;
  if(i<width && atomicAdd(values+i,0u)!=i+1)atomicOr(bad,1ull<<i);
}

int main() {
  HIP(hipSetDevice(0));
  hipDeviceProp_t prop{};HIP(hipGetDeviceProperties(&prop,0));
  std::fprintf(stderr,"DEVICE %s CUs=%d\n",prop.gcnArchName,prop.multiProcessorCount);
  for(const char* flag:{"GPU_NATIVE_EVENT_WAIT","GPU_NATIVE_EVENT_DIAGNOSTIC_MIN_DISPATCHES",
       "GPU_GRAPH_DIAGNOSTIC_LONGPATH","GPU_GRAPH_DIAGNOSTIC_SIDEWAIT",
       "DEBUG_HIP_FORCE_GRAPH_QUEUES","GPU_MAX_HW_QUEUES"}) {
    const char* v=std::getenv(flag);std::fprintf(stderr,"CONTROL %s=%s\n",flag,v?v:"unset");
  }
  hipStream_t launch;HIP(hipStreamCreateWithFlags(&launch,hipStreamNonBlocking));
  unsigned* values;unsigned long long* device_bad;unsigned long long* host_bad;
  HIP(hipMalloc(&values,32*sizeof(unsigned)));HIP(hipMalloc(&device_bad,sizeof(*device_bad)));
  HIP(hipHostMalloc(&host_bad,sizeof(*host_bad)));
  std::puts("width,creation_order,iteration,observed_bad_mask,eventual_correct,ordered_complete");
  for(unsigned width:{6u,9u,15u,23u})for(unsigned order=0;order<3;++order) {
    std::vector<unsigned> ids(width);std::iota(ids.begin(),ids.end(),0);
    if(order==1)std::reverse(ids.begin(),ids.end());
    if(order==2){std::mt19937 rng(9817+width);std::shuffle(ids.begin(),ids.end(),rng);}
    hipGraph_t graph;HIP(hipGraphCreate(&graph,0));
    for(unsigned branch:ids) {
      // Average chain length exceeds8, retaining default segmented scheduling
      // even when the graph has >=16 independent terminal branches.
      unsigned length=8+(branch*5)%9;
      hipGraphNode_t previous=nullptr;
      for(unsigned k=0;k<length;++k) {
        unsigned final_step=(k+1==length);
        unsigned long long cycles=final_step?2000000ull*(1+branch%5):1000ull;
        void* args[]={&values,&branch,&final_step,&cycles};
        hipKernelNodeParams params{};params.func=reinterpret_cast<void*>(terminal_step);
        params.gridDim=dim3(1);params.blockDim=dim3(64);params.kernelParams=args;
        hipGraphNode_t node;HIP(hipGraphAddKernelNode(&node,graph,previous?&previous:nullptr,previous?1:0,&params));
        previous=node;
      }
    }
    hipGraphExec_t exec;HIP(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
    for(unsigned iteration=0;iteration<4;++iteration) {
      // Initial synchronization only prepares a known state before the tested
      // graph. No device-wide synchronization is inserted after graph launch
      // until after the launch-stream checksum has been copied and observed.
      HIP(hipMemset(values,0,32*sizeof(unsigned)));HIP(hipMemset(device_bad,0,sizeof(*device_bad)));
      HIP(hipDeviceSynchronize());
      HIP(hipGraphLaunch(exec,launch));
      observe_completion<<<1,64,0,launch>>>(values,width,device_bad);HIP(hipGetLastError());
      HIP(hipMemcpyAsync(host_bad,device_bad,sizeof(*host_bad),hipMemcpyDeviceToHost,launch));
      HIP(hipStreamSynchronize(launch));
      const auto observed=*host_bad;
      // Drain only after preserving the actual observation. Distinguish early
      // graph completion from bad kernel arithmetic/parameters and prepare reuse.
      HIP(hipDeviceSynchronize());std::vector<unsigned> final_values(width);
      HIP(hipMemcpy(final_values.data(),values,width*sizeof(unsigned),hipMemcpyDeviceToHost));
      bool eventual=true;for(unsigned i=0;i<width;++i)eventual&=(final_values[i]==i+1);
      std::printf("%u,%u,%u,%llu,%u,%u\n",width,order,iteration,observed,unsigned(eventual),unsigned(observed==0));
      std::fflush(stdout);if(!eventual)return 3;
    }
    const char* dot=std::getenv("DEBUG_HIP_GRAPH_DOT_PRINT");
    if(dot && std::string(dot)=="1") {
      std::string original="graph_"+std::to_string(getpid())+"_dot_print_launch_1";
      std::string saved="terminal-w"+std::to_string(width)+"-o"+std::to_string(order)+"-launch.dot";
      int result=std::rename(original.c_str(),saved.c_str());
      std::fprintf(stderr,"SEGMENTED_LAUNCH width=%u order=%u captured=%u\n",width,order,unsigned(result==0));
    }
    HIP(hipGraphExecDestroy(exec));HIP(hipGraphDestroy(graph));
  }
  HIP(hipStreamDestroy(launch));HIP(hipFree(values));HIP(hipFree(device_bad));HIP(hipHostFree(host_bad));
  return 0;
}
