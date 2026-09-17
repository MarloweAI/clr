// Exercise a real host-callback dependency between two substantial dispatch prefixes.
#include <hip/hip_runtime.h>
#include <atomic>
#include <chrono>
#include <thread>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#define HIP(x) do{auto checked=(x);if(checked!=hipSuccess){fprintf(stderr,"line%d %s\n",__LINE__,hipGetErrorString(checked));exit(2);}}while(0)
struct Gate {std::atomic<bool> entered{false},release{false},watchdog{false};};
void callback(void* arg){auto& gate=*static_cast<Gate*>(arg);gate.entered.store(true,std::memory_order_release);while(!gate.release.load(std::memory_order_acquire))std::this_thread::yield();}
__global__ void increment(unsigned* p){++*p;}
__global__ void consume(const unsigned* p,unsigned* out){*out=*p;}
int main(){
 int devices;HIP(hipGetDeviceCount(&devices));if(devices!=1||!getenv("SLURM_JOB_ID"))return 2;
 std::ifstream maps("/proc/self/maps");for(std::string s;std::getline(maps,s);)if(s.find("libamdhip64")!=std::string::npos||s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
 hipStream_t p,c;HIP(hipStreamCreateWithFlags(&p,hipStreamNonBlocking));HIP(hipStreamCreateWithFlags(&c,hipStreamNonBlocking));
 hipEvent_t ready;HIP(hipEventCreateWithFlags(&ready,hipEventDisableTiming));unsigned *value,*out;HIP(hipMalloc(&value,4));HIP(hipMalloc(&out,4));
 hipGraph_t graph;hipGraphExec_t exec;HIP(hipStreamBeginCapture(p,hipStreamCaptureModeGlobal));for(int i=0;i<300;++i)increment<<<1,1,0,p>>>(value);HIP(hipStreamEndCapture(p,&graph));HIP(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
 puts("trial,pending,watchdog,correct");
 for(int trial=0;trial<16;++trial){
  HIP(hipMemsetAsync(value,0,4,p));HIP(hipMemsetAsync(out,0xff,4,p));HIP(hipStreamSynchronize(p));Gate gate;
  std::thread watchdog([&]{auto until=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!gate.release.load(std::memory_order_acquire)){if(std::chrono::steady_clock::now()>until){gate.watchdog.store(true);gate.release.store(true,std::memory_order_release);break;}std::this_thread::sleep_for(std::chrono::milliseconds(1));}});
  HIP(hipGraphLaunch(exec,p));HIP(hipLaunchHostFunc(p,callback,&gate));HIP(hipGraphLaunch(exec,p));HIP(hipEventRecord(ready,p));
  auto state=hipEventQuery(ready);if(state!=hipSuccess&&state!=hipErrorNotReady)HIP(state);
  HIP(hipStreamWaitEvent(c,ready,0));consume<<<1,1,0,c>>>(value,out);HIP(hipGetLastError());gate.release.store(true,std::memory_order_release);watchdog.join();HIP(hipStreamSynchronize(c));
  unsigned got;HIP(hipMemcpy(&got,out,4,hipMemcpyDeviceToHost));if(got!=600||!gate.entered.load()||gate.watchdog.load()||state!=hipErrorNotReady)return 3;
  printf("%d,1,0,1\n",trial);
 }
 HIP(hipGraphExecDestroy(exec));HIP(hipGraphDestroy(graph));HIP(hipEventDestroy(ready));HIP(hipStreamDestroy(p));HIP(hipStreamDestroy(c));HIP(hipFree(value));HIP(hipFree(out));
}
