#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#define H(x) do {auto fixture_status=(x);if(fixture_status!=hipSuccess){std::fprintf(stderr,"line%d %s %s\n",__LINE__,#x,hipGetErrorString(fixture_status));std::exit(2);}}while(0)
__global__ void producer(int* data,int branch,unsigned long long delay){auto t=wall_clock64();while(wall_clock64()-t<delay){}if(threadIdx.x==0)data[branch]=17+2*branch;}
__global__ void consume(int* data){if(threadIdx.x==0)data[2]=3*data[0]+5*data[1];}
int main(int argc,char** argv){
 int delayed=argc>1?std::atoi(argv[1]):1;
 H(hipSetDevice(0));int rate;H(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));int* data;H(hipMalloc(&data,3*sizeof(int)));hipStream_t stream;H(hipStreamCreateWithFlags(&stream,hipStreamNonBlocking));H(hipMemsetAsync(data,0,3*sizeof(int),stream));
 hipGraph_t g[2];hipGraphExec_t e[2];for(auto& x:g)H(hipGraphCreate(&x,0));
 for(int b=0;b<2;++b){unsigned long long delay=b==delayed?static_cast<unsigned long long>(rate)*20:0;void* args[]={&data,&b,&delay};hipKernelNodeParams p{};p.func=(void*)producer;p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;hipGraphNode_t n;H(hipGraphAddKernelNode(&n,g[0],nullptr,0,&p));}
 void* args[]={&data};hipKernelNodeParams p{};p.func=(void*)consume;p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;hipGraphNode_t n;H(hipGraphAddKernelNode(&n,g[1],nullptr,0,&p));for(int i=0;i<2;++i)H(hipGraphInstantiate(&e[i],g[i],nullptr,nullptr,0));
 H(hipGraphLaunch(e[0],stream));H(hipGraphLaunch(e[1],stream));int result[3];H(hipMemcpyAsync(result,data,sizeof(result),hipMemcpyDeviceToHost,stream));H(hipStreamSynchronize(stream));bool ok=result[0]==17&&result[1]==19&&result[2]==146;
 for(int i=0;i<2;++i){H(hipGraphExecDestroy(e[i]));H(hipGraphDestroy(g[i]));}H(hipStreamDestroy(stream));H(hipFree(data));std::printf("{\"passed\":%s,\"delayed_branch\":%d,\"values\":[%d,%d,%d],\"expected\":[17,19,146]}\n",ok?"true":"false",delayed,result[0],result[1],result[2]);return ok?0:3;
}
