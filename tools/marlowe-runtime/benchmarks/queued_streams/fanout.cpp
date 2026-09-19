#include <hip/hip_runtime.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#define HIP(x) do {auto e=(x);if(e!=hipSuccess){fprintf(stderr,"line %d %s: %s\n",__LINE__,#x,hipGetErrorString(e));exit(2);}}while(0)
__global__ void increment(unsigned* p) { ++*p; }
__global__ void produce_end(unsigned long long* p) { *p=wall_clock64(); }
__global__ void consume(const unsigned* p,unsigned* out,unsigned long long* t) { *out=*p; *t=wall_clock64(); }
// Controlled delayed execution, excluded from producer timing. This cell tests
// a wait admitted at submission that is already satisfied when it executes.
__global__ void delay_execution(unsigned long long ticks) { auto start=wall_clock64(); while(wall_clock64()-start<ticks) {} }
int main(int argc,char** argv) {
  if(argc!=2||!getenv("SLURM_JOB_ID")) return 2;
  int repeats=std::stoi(argv[1]),count,rate; if(repeats<3) return 2;
  HIP(hipGetDeviceCount(&count)); if(count!=1) return 2;
  HIP(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
  std::ifstream maps("/proc/self/maps");for(std::string s;std::getline(maps,s);)if(s.find("libamdhip64")!=std::string::npos||s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
  hipStream_t p,c[3]; hipEvent_t begin,end,dummy,stop[3];
  HIP(hipStreamCreateWithFlags(&p,hipStreamNonBlocking));
  for(int i=0;i<3;++i) { HIP(hipStreamCreateWithFlags(&c[i],hipStreamNonBlocking)); HIP(hipEventCreate(&stop[i])); }
  HIP(hipEventCreate(&begin)); HIP(hipEventCreate(&end)); HIP(hipEventCreateWithFlags(&dummy,hipEventDisableTiming));
  HIP(hipEventRecord(dummy,c[0])); HIP(hipEventSynchronize(dummy));
  unsigned *value,*results; unsigned long long* times;
  HIP(hipMalloc(&value,4)); HIP(hipMalloc(&results,12)); HIP(hipMalloc(&times,32));
  hipGraph_t graph; hipGraphExec_t exec;
  HIP(hipStreamBeginCapture(p,hipStreamCaptureModeGlobal));
  for(int i=0;i<128;++i) increment<<<1,1,0,p>>>(value);
  HIP(hipStreamEndCapture(p,&graph)); HIP(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
  puts("consumers,consumer_delay_us,trial,producer_us,total_us,resume_gap_us,host_us,correct");
  for(int consumers:{1,2,3}) for(int delay:{0,5000}) for(int trial=-3;trial<repeats;++trial) {
    HIP(hipMemsetAsync(value,0,4,p)); HIP(hipMemsetAsync(results,0xff,12,p)); HIP(hipMemsetAsync(times,0,32,p)); HIP(hipStreamSynchronize(p));
    auto host_begin=std::chrono::steady_clock::now();
    if(delay) for(int i=0;i<consumers;++i) delay_execution<<<1,1,0,c[i]>>>(static_cast<unsigned long long>(delay)*rate/1000);
    HIP(hipEventRecord(begin,p));
    for(int chunk=0;chunk<16;++chunk) { HIP(hipGraphLaunch(exec,p)); HIP(hipStreamWaitEvent(p,dummy,0)); }
    produce_end<<<1,1,0,p>>>(times); HIP(hipEventRecord(end,p));
    for(int i=0;i<consumers;++i) { HIP(hipStreamWaitEvent(c[i],end,0)); consume<<<1,1,0,c[i]>>>(value,results+i,times+1+i); HIP(hipEventRecord(stop[i],c[i])); }
    HIP(hipGetLastError()); for(int i=0;i<consumers;++i) HIP(hipEventSynchronize(stop[i]));
    double host=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-host_begin).count();
    unsigned actual[3]; unsigned long long stamps[4]; HIP(hipMemcpy(actual,results,12,hipMemcpyDeviceToHost)); HIP(hipMemcpy(stamps,times,32,hipMemcpyDeviceToHost));
    float producer_ms; HIP(hipEventElapsedTime(&producer_ms,begin,end)); double total=0,gap=0;
    for(int i=0;i<consumers;++i) { if(actual[i]!=2048||!stamps[0]||stamps[i+1]<stamps[0]) return 3; float ms; HIP(hipEventElapsedTime(&ms,begin,stop[i])); total=std::max(total,double(ms)*1000); gap=std::max(gap,(stamps[i+1]-stamps[0])*1000.0/rate); }
    if(trial>=0) printf("%d,%d,%d,%.3f,%.3f,%.3f,%.3f,1\n",consumers,delay,trial,producer_ms*1000,total,gap,host);
  }
  HIP(hipGraphExecDestroy(exec)); HIP(hipGraphDestroy(graph)); HIP(hipEventDestroy(begin)); HIP(hipEventDestroy(end)); HIP(hipEventDestroy(dummy));
  for(int i=0;i<3;++i) { HIP(hipEventDestroy(stop[i])); HIP(hipStreamDestroy(c[i])); }
  HIP(hipStreamDestroy(p)); HIP(hipFree(value)); HIP(hipFree(results)); HIP(hipFree(times));
}
