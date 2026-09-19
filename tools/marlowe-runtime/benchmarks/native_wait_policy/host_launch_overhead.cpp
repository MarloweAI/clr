// Measure real host submission cost, including any queue backpressure, with and
// without per-launch profiling markers. No stream waits: the native path has no benefit here.
#include <hip/hip_runtime.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#define HIP(x) do {auto checked=(x);if(checked!=hipSuccess){fprintf(stderr,"line%d %s\n",__LINE__,hipGetErrorString(checked));exit(2);}}while(0)
__global__ void increment(unsigned* value){++*value;}
int main(int argc,char**argv){
 if(argc!=2||!getenv("SLURM_JOB_ID"))return 2;int n=std::stoi(argv[1]),devices;
 HIP(hipGetDeviceCount(&devices));if(devices!=1)return 2;
 std::ifstream maps("/proc/self/maps");for(std::string s;std::getline(maps,s);)if(s.find("libamdhip64")!=std::string::npos||s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
 hipStream_t stream;HIP(hipStreamCreateWithFlags(&stream,hipStreamNonBlocking));
 hipEvent_t profile,begin,end;HIP(hipEventCreate(&profile));HIP(hipEventCreate(&begin));HIP(hipEventCreate(&end));unsigned* value;HIP(hipMalloc(&value,4));
 puts("profiled,kernels,trial,submit_us,host_us,gpu_us,correct");
 for(int trial=-1;trial<3;++trial)for(int order=0;order<2;++order){
  int profiled=(order+trial+2)%2;HIP(hipMemsetAsync(value,0,4,stream));HIP(hipStreamSynchronize(stream));HIP(hipEventRecord(begin,stream));
  auto start=std::chrono::steady_clock::now();
  for(int i=0;i<n;++i){increment<<<1,1,0,stream>>>(value);if(profiled)HIP(hipEventRecord(profile,stream));}
  HIP(hipGetLastError());auto submitted=std::chrono::steady_clock::now();HIP(hipEventRecord(end,stream));HIP(hipEventSynchronize(end));auto stop=std::chrono::steady_clock::now();
  float ms;HIP(hipEventElapsedTime(&ms,begin,end));unsigned got;HIP(hipMemcpy(&got,value,4,hipMemcpyDeviceToHost));if(got!=unsigned(n))return 3;
  if(trial>=0)printf("%d,%d,%d,%.3f,%.3f,%.3f,1\n",profiled,n,trial,std::chrono::duration<double,std::micro>(submitted-start).count(),std::chrono::duration<double,std::micro>(stop-start).count(),ms*1000);
 }
 HIP(hipFree(value));HIP(hipEventDestroy(profile));HIP(hipEventDestroy(begin));HIP(hipEventDestroy(end));HIP(hipStreamDestroy(stream));
}
