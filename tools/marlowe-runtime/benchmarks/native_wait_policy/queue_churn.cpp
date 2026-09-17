// Race ordinary queue creation/recycling with substantial pending producer waits.
#include <hip/hip_runtime.h>
#include <atomic>
#include <thread>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#define HIP(x) do{auto checked=(x);if(checked!=hipSuccess){fprintf(stderr,"line%d %s\n",__LINE__,hipGetErrorString(checked));exit(2);}}while(0)
__global__ void increment(unsigned* p){++*p;}
__global__ void consume(const unsigned* p,unsigned* out){*out=*p;}
int main(){
 int devices;HIP(hipGetDeviceCount(&devices));if(devices!=1||!getenv("SLURM_JOB_ID"))return 2;
 std::ifstream maps("/proc/self/maps");for(std::string s;std::getline(maps,s);)if(s.find("libamdhip64")!=std::string::npos||s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
 hipStream_t p,c;HIP(hipStreamCreateWithFlags(&p,hipStreamNonBlocking));HIP(hipStreamCreateWithFlags(&c,hipStreamNonBlocking));hipEvent_t ready;HIP(hipEventCreateWithFlags(&ready,hipEventDisableTiming));
 unsigned *value,*out,*scratch;HIP(hipMalloc(&value,4));HIP(hipMalloc(&out,4));HIP(hipMalloc(&scratch,8*4));HIP(hipMemsetAsync(value,0,4,p));HIP(hipMemsetAsync(out,0,4,c));HIP(hipDeviceSynchronize());
 hipGraph_t graph;hipGraphExec_t exec;HIP(hipStreamBeginCapture(p,hipStreamCaptureModeGlobal));for(int i=0;i<2048;++i)increment<<<1,1,0,p>>>(value);HIP(hipStreamEndCapture(p,&graph));HIP(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
 std::atomic<bool> started{false},stop{false};std::atomic<unsigned> cycles{0};
 std::thread churn([&]{HIP(hipSetDevice(0));while(!stop.load(std::memory_order_acquire)){
  hipStream_t streams[8];for(int i=0;i<8;++i){HIP(hipStreamCreateWithFlags(&streams[i],hipStreamNonBlocking));HIP(hipMemsetAsync(scratch+i,0,4,streams[i]));for(int j=0;j<10;++j)increment<<<1,1,0,streams[i]>>>(scratch+i);}
  for(int i=0;i<8;++i){HIP(hipStreamSynchronize(streams[i]));unsigned got;HIP(hipMemcpy(&got,scratch+i,4,hipMemcpyDeviceToHost));if(got!=10)exit(3);HIP(hipStreamDestroy(streams[i]));}
  cycles.fetch_add(1);started.store(true,std::memory_order_release);
 }});
 while(!started.load(std::memory_order_acquire))std::this_thread::yield();
 puts("trial,pending,correct");
 for(int trial=0;trial<128;++trial){HIP(hipMemsetAsync(value,0,4,p));HIP(hipGraphLaunch(exec,p));HIP(hipEventRecord(ready,p));auto state=hipEventQuery(ready);if(state!=hipSuccess&&state!=hipErrorNotReady)HIP(state);HIP(hipStreamWaitEvent(c,ready,0));consume<<<1,1,0,c>>>(value,out);HIP(hipGetLastError());HIP(hipStreamSynchronize(c));unsigned got;HIP(hipMemcpy(&got,out,4,hipMemcpyDeviceToHost));if(got!=2048)exit(4);printf("%d,%d,1\n",trial,int(state==hipErrorNotReady));}
 stop.store(true,std::memory_order_release);churn.join();fprintf(stderr,"CHURN_CYCLES=%u\n",cycles.load());if(cycles.load()<2)return 5;
 HIP(hipGraphExecDestroy(exec));HIP(hipGraphDestroy(graph));HIP(hipEventDestroy(ready));HIP(hipStreamDestroy(p));HIP(hipStreamDestroy(c));HIP(hipFree(value));HIP(hipFree(out));HIP(hipFree(scratch));
}
