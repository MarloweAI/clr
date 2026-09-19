// Active kernel-only entry: external H2D, full-buffer writes, D2H and public completion.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <initializer_list>
#include <cstdlib>
#include <thread>
#include <chrono>
#define H(x) do{auto e=(x);if(e!=hipSuccess){std::fprintf(stderr,"%d %s: %s\n",__LINE__,#x,hipGetErrorString(e));std::exit(2);}}while(0)
__global__ void transform(const unsigned* src,unsigned* dst,unsigned begin,unsigned count){unsigned j=blockIdx.x*blockDim.x+threadIdx.x;if(j<count){unsigned i=begin+j;dst[i]=src[i]^(0xa5a55a5au+i*2654435761u);}}
int main(){
 H(hipSetDevice(0));hipStream_t stream;H(hipStreamCreateWithFlags(&stream,hipStreamNonBlocking));
 hipEvent_t event,timeless;H(hipEventCreate(&event));H(hipEventCreateWithFlags(&timeless,hipEventDisableTiming));
 std::puts("bytes,completion,epoch,mismatches,correct");
 for(size_t bytes:{size_t(65536),size_t(8*1024*1024)}){
  unsigned n=bytes/4;unsigned *src,*dst[2],*in[2],*out[2];H(hipMalloc(&src,bytes));hipGraph_t graph[2];hipGraphExec_t exec[2];
  for(unsigned epoch=0;epoch<2;++epoch){H(hipMalloc(&dst[epoch],bytes));H(hipHostMalloc(&in[epoch],bytes));H(hipHostMalloc(&out[epoch],bytes));
   H(hipGraphCreate(&graph[epoch],0));unsigned branch=0;
   for(unsigned length:{8u,16u,9u,12u}){hipGraphNode_t prev=nullptr;unsigned begin=branch*(n/4),count=n/4;
    for(unsigned k=0;k<length;++k){void* args[]={&src,&dst[epoch],&begin,&count};hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(transform);p.gridDim=dim3((count+255)/256);p.blockDim=dim3(256);p.kernelParams=args;hipGraphNode_t node;H(hipGraphAddKernelNode(&node,graph[epoch],prev?&prev:nullptr,prev?1:0,&p));prev=node;}++branch;
   }H(hipGraphInstantiate(&exec[epoch],graph[epoch],nullptr,nullptr,0));
  }
  for(unsigned completion=0;completion<4;++completion){
   for(unsigned epoch=0;epoch<2;++epoch){
    // Each completion method must publish a fresh pattern, so previous correct
    // device contents cannot mask a lost or stale graph result.
    for(unsigned i=0;i<n;++i){in[epoch][i]=(epoch?0xf0a5c391u:0x195ace03u)+completion*0x10203129u+i*1103515245u;out[epoch][i]=0;}
    H(hipMemcpyAsync(src,in[epoch],bytes,hipMemcpyHostToDevice,stream));
    H(hipGraphLaunch(exec[epoch],stream));
    H(hipMemcpyAsync(out[epoch],dst[epoch],bytes,hipMemcpyDeviceToHost,stream));
   }
   if(completion==0)H(hipStreamSynchronize(stream));
   else if(completion==1){H(hipEventRecord(event,stream));H(hipEventSynchronize(event));}
   else if(completion==2){H(hipEventRecord(timeless,stream));H(hipEventSynchronize(timeless));}
   else {hipError_t status;while((status=hipStreamQuery(stream))==hipErrorNotReady)std::this_thread::sleep_for(std::chrono::microseconds(50));H(status);}
   for(unsigned epoch=0;epoch<2;++epoch){unsigned bad=0;for(unsigned i=0;i<n;++i)bad+=out[epoch][i]!=(in[epoch][i]^(0xa5a55a5au+i*2654435761u));std::printf("%zu,%u,%u,%u,%u\n",bytes,completion,epoch,bad,unsigned(!bad));std::fflush(stdout);if(bad)return 3;}
  }
  for(unsigned epoch=0;epoch<2;++epoch){H(hipGraphExecDestroy(exec[epoch]));H(hipGraphDestroy(graph[epoch]));H(hipFree(dst[epoch]));H(hipHostFree(in[epoch]));H(hipHostFree(out[epoch]));}H(hipFree(src));
 }
 H(hipEventDestroy(event));H(hipEventDestroy(timeless));H(hipStreamDestroy(stream));
}
