#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#define H(x) do{auto hip_status_result=(x);if(hip_status_result!=hipSuccess){std::fprintf(stderr,"%d %s: %s\n",__LINE__,#x,hipGetErrorString(hip_status_result));std::exit(2);}}while(0)
__global__ void reset(unsigned* v){if(threadIdx.x==0){auto t=clock64();while(clock64()-t<20000000ull){};*v=0;}}
__global__ void inc(unsigned* v){if(threadIdx.x==0)atomicAdd(v,1u);}
int main(){
 H(hipSetDevice(0));unsigned* v;H(hipMalloc(&v,sizeof(*v)));hipStream_t s;H(hipStreamCreateWithFlags(&s,hipStreamNonBlocking));
 hipGraph_t g;H(hipGraphCreate(&g,0));std::vector<std::vector<hipGraphNode_t>> branches;
 for(unsigned length:{8u,16u,9u,12u,8u,16u,9u,12u,8u}){
  branches.emplace_back();hipGraphNode_t prev=nullptr;
  for(unsigned k=0;k<length;++k){void* args[]={&v};hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(inc);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;hipGraphNode_t n;H(hipGraphAddKernelNode(&n,g,prev?&prev:nullptr,prev?1:0,&p));prev=n;branches.back().push_back(n);}
 }
 hipGraphExec_t e;H(hipGraphInstantiate(&e,g,nullptr,nullptr,0));std::puts("state,epoch,expected,observed,correct");
 for(unsigned epoch=0;epoch<2;++epoch)for(unsigned state=0;state<6;++state){unsigned expected=0;
  for(unsigned b=0;b<branches.size();++b)for(unsigned k=0;k<branches[b].size();++k){bool enabled= !(state==1&&b==0&&k==0) && !(state==2&&k==0) && !(state==3&&b==0) && state!=4;H(hipGraphNodeSetEnabled(e,branches[b][k],unsigned(enabled)));expected+=enabled;}
  reset<<<1,64,0,s>>>(v);H(hipGetLastError());H(hipGraphLaunch(e,s));unsigned observed=~0u;H(hipMemcpyAsync(&observed,v,sizeof(observed),hipMemcpyDeviceToHost,s));H(hipStreamSynchronize(s));
  std::printf("%u,%u,%u,%u,%u\n",state,epoch,expected,observed,unsigned(expected==observed));std::fflush(stdout);if(expected!=observed)return 3;
 }
 H(hipGraphExecDestroy(e));H(hipGraphDestroy(g));H(hipStreamDestroy(s));H(hipFree(v));
}
