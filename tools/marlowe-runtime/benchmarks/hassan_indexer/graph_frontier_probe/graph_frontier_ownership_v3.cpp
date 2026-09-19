#include <hip/hip_runtime.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#define H(x) do {auto e=(x);if(e!=hipSuccess){std::fprintf(stderr,"line%d %s %s\n",__LINE__,#x,hipGetErrorString(e));std::exit(2);}}while(0)
#define R(x) do {if(!(x)){std::fprintf(stderr,"line%d failed %s\n",__LINE__,#x);std::exit(3);}}while(0)
int main(int argc,char**argv){
 R(argc==4);bool early=std::atoi(argv[3])!=0;H(hipSetDevice(0));int rate;H(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
 hipModule_t modules[2];hipFunction_t functions[2];for(int i=0;i<2;++i){H(hipModuleLoad(&modules[i],argv[i+1]));H(hipModuleGetFunction(&functions[i],modules[i],"write_value"));}
 int* output;H(hipMalloc(&output,4*sizeof(int)));H(hipMemset(output,0,4*sizeof(int)));hipStream_t stream;H(hipStreamCreateWithFlags(&stream,hipStreamNonBlocking));
 hipGraph_t graph;hipGraphExec_t exec;hipGraphNode_t nodes[2];H(hipGraphCreate(&graph,0));
 for(int i=0;i<2;++i){int value=10+i;unsigned long long delay=static_cast<unsigned long long>(rate)*200;void* args[]={&output,&i,&value,&delay};hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(functions[0]);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;H(hipGraphAddKernelNode(&nodes[i],graph,nullptr,0,&p));}
 H(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));H(hipGraphLaunch(exec,stream));
 auto before=std::chrono::steady_clock::now();
 for(int i=0;i<2;++i){int slot=2+i,value=20+i;unsigned long long delay=0;void* args[]={&output,&slot,&value,&delay};hipKernelNodeParams p{};p.func=reinterpret_cast<void*>(functions[1]);p.gridDim=dim3(1);p.blockDim=dim3(64);p.kernelParams=args;H(hipGraphExecKernelNodeSetParams(exec,nodes[i],&p));}
 H(hipGraphLaunch(exec,stream));auto updated=std::chrono::steady_clock::now();
 if(early)H(hipModuleUnload(modules[0]));auto unloaded=std::chrono::steady_clock::now();
 H(hipGraphExecDestroy(exec));H(hipGraphDestroy(graph));if(early)H(hipModuleUnload(modules[1]));H(hipStreamSynchronize(stream));if(!early){H(hipModuleUnload(modules[0]));H(hipModuleUnload(modules[1]));}
 int actual[4];H(hipMemcpy(actual,output,sizeof(actual),hipMemcpyDeviceToHost));R(actual[0]==11&&actual[1]==12&&actual[2]==37&&actual[3]==38);
 H(hipStreamDestroy(stream));H(hipFree(output));
 std::printf("{\"passed\":true,\"checked_values\":4,\"function_update_ms\":%.6f,\"first_module_unload_ms\":%.6f,\"destroyed_before_sync\":true}\n",std::chrono::duration<double,std::milli>(updated-before).count(),std::chrono::duration<double,std::milli>(unloaded-updated).count());
}
