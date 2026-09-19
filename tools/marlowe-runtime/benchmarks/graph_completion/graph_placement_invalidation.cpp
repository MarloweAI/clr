#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#define H(x) do { auto e=(x); if(e!=hipSuccess){std::fprintf(stderr,"line%d %s: %s\n",__LINE__,#x,hipGetErrorString(e));std::exit(2);} } while(0)
#define REQUIRE(x) do { if(!(x)){std::fprintf(stderr,"line%d failed: %s\n",__LINE__,#x);std::exit(3);} } while(0)
extern "C" int placement_device(hipGraphExec_t);
__global__ void increment(unsigned* value){if(threadIdx.x==0)atomicAdd(value,1u);}
struct Fixture {
 hipGraph_t graph=nullptr;hipGraphNode_t first=nullptr;hipGraphExec_t exec=nullptr;
 unsigned* value=nullptr;hipKernelNodeParams params{};void* args[1]{};
 Fixture(){
  H(hipSetDevice(0));H(hipMalloc(&value,sizeof(*value)));args[0]=&value;
  params.func=reinterpret_cast<void*>(increment);params.gridDim=dim3(1);params.blockDim=dim3(64);params.kernelParams=args;
  H(hipGraphCreate(&graph,0));
  for(unsigned length:{8,16,9,12}){hipGraphNode_t prev=nullptr;
   for(unsigned i=0;i<length;++i){hipGraphNode_t n;H(hipGraphAddKernelNode(&n,graph,prev?&prev:nullptr,prev?1:0,&params));if(!first)first=n;prev=n;}
  }
  H(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));REQUIRE(placement_device(exec)==0);
 }
 void replay(){
  H(hipSetDevice(0));hipStream_t stream;H(hipStreamCreateWithFlags(&stream,hipStreamNonBlocking));
  H(hipMemsetAsync(value,0,sizeof(*value),stream));H(hipGraphLaunch(exec,stream));H(hipStreamSynchronize(stream));
  unsigned result=0;H(hipMemcpy(&result,value,sizeof(result),hipMemcpyDeviceToHost));REQUIRE(result==45);H(hipStreamDestroy(stream));
 }
 ~Fixture(){H(hipSetDevice(0));H(hipGraphExecDestroy(exec));H(hipGraphDestroy(graph));H(hipFree(value));}
};
int main(){
 int devices=0;H(hipGetDeviceCount(&devices));REQUIRE(devices>=2);
 std::puts("case,initial_device,after_rejection,after_restore,rebuilt_device,correct");
 for(const std::string kind:{"specific","generic"}){
  Fixture f;
  H(hipGraphExecKernelNodeSetParams(f.exec,f.first,&f.params));REQUIRE(placement_device(f.exec)==0);f.replay();
  // A source-graph mutation must not invalidate the already cloned executable.
  H(hipSetDevice(1));auto bad=f.params;bad.blockDim=dim3(0);
  REQUIRE(hipGraphKernelNodeSetParams(f.first,&bad)!=hipSuccess);REQUIRE(placement_device(f.exec)==0);
  H(hipSetDevice(0));H(hipGraphKernelNodeSetParams(f.first,&f.params));
  H(hipSetDevice(1));hipError_t rejected;
  if(kind=="specific")rejected=hipGraphExecKernelNodeSetParams(f.exec,f.first,&bad);
  else {hipGraphNodeParams p{};p.type=hipGraphNodeTypeKernel;p.kernel=bad;rejected=hipGraphExecNodeSetParams(f.exec,f.first,&p);}
  REQUIRE(rejected!=hipSuccess);REQUIRE(placement_device(f.exec)==-1);
  H(hipSetDevice(0));H(hipGraphExecKernelNodeSetParams(f.exec,f.first,&f.params));REQUIRE(placement_device(f.exec)==-1);f.replay();
  H(hipGraphExecDestroy(f.exec));f.exec=nullptr;H(hipGraphInstantiate(&f.exec,f.graph,nullptr,nullptr,0));REQUIRE(placement_device(f.exec)==0);f.replay();
  std::printf("%s,0,-1,-1,0,1\n",kind.c_str());
 }
}
