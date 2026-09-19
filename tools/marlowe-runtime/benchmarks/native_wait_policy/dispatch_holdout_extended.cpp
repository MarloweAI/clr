// Holdout dispatch lengths, eager/graph submission, and delayed event waits.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <chrono>
#include <thread>
#define HIP(x) do {auto e=(x);if(e!=hipSuccess){fprintf(stderr,"line%d %s: %s\n",__LINE__,#x,hipGetErrorString(e));exit(2);}}while(0)
__global__ void increment(unsigned* p){++*p;}
__global__ void stamp(unsigned long long* p,int i){p[i]=wall_clock64();}
__global__ void consume(const unsigned* p,unsigned* result,unsigned long long* t){t[1]=wall_clock64();*result=*p;}
int main(int argc,char** argv){
 if(argc!=2||!getenv("SLURM_JOB_ID"))return 2;int repeats=std::stoi(argv[1]);
 int count,rate;HIP(hipGetDeviceCount(&count));if(count!=1)return 2;HIP(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
 std::ifstream maps("/proc/self/maps");for(std::string s;std::getline(maps,s);)if(s.find("libamdhip64")!=std::string::npos||s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
 hipStream_t producer,consumer;HIP(hipStreamCreateWithFlags(&producer,hipStreamNonBlocking));HIP(hipStreamCreateWithFlags(&consumer,hipStreamNonBlocking));
 hipEvent_t begin,end,stop;HIP(hipEventCreate(&begin));HIP(hipEventCreate(&end));HIP(hipEventCreate(&stop));
 unsigned *value,*result;unsigned long long* times;HIP(hipMalloc(&value,4));HIP(hipMalloc(&result,4));HIP(hipMalloc(&times,16));
 puts("submission,kernels,delay_us,trial,schedule,producer_us,total_us,resume_gap_us,host_us,pending,correct");
 for(int eager:{0,1})for(int n:{32,128,256,384,512,768,2048,4096}){
  hipGraph_t graph;hipGraphExec_t exec;HIP(hipStreamBeginCapture(producer,hipStreamCaptureModeGlobal));
  for(int i=0;i<n;++i)increment<<<1,1,0,producer>>>(value);stamp<<<1,1,0,producer>>>(times,0);
  HIP(hipStreamEndCapture(producer,&graph));HIP(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
  for(int delay:{0,1000,2500,2950,3050,3150}){
   if(delay&&n!=2048)continue;
   for(int trial=-2;trial<repeats;++trial)for(int order=0;order<2;++order){
    int side=(order+trial+2)%2;
    HIP(hipMemsetAsync(value,0,4,producer));HIP(hipMemsetAsync(result,0xff,4,producer));HIP(hipMemsetAsync(times,0,16,producer));HIP(hipStreamSynchronize(producer));
    auto host_start=std::chrono::steady_clock::now();HIP(hipEventRecord(begin,producer));
    if(eager){for(int i=0;i<n;++i)increment<<<1,1,0,producer>>>(value);stamp<<<1,1,0,producer>>>(times,0);}
    else HIP(hipGraphLaunch(exec,producer));
    HIP(hipEventRecord(end,producer));
    if(delay)std::this_thread::sleep_for(std::chrono::microseconds(delay));
    auto status=hipEventQuery(end);if(status!=hipSuccess&&status!=hipErrorNotReady)HIP(status);bool pending=status==hipErrorNotReady;
    hipStream_t target=side?consumer:producer;
    if(side)HIP(hipStreamWaitEvent(consumer,end,0));
    consume<<<1,1,0,target>>>(value,result,times);HIP(hipGetLastError());HIP(hipEventRecord(stop,target));HIP(hipEventSynchronize(stop));
    auto host_end=std::chrono::steady_clock::now();float producer_ms,total_ms;HIP(hipEventElapsedTime(&producer_ms,begin,end));HIP(hipEventElapsedTime(&total_ms,begin,stop));
    unsigned output;unsigned long long timestamps[2];HIP(hipMemcpy(&output,result,4,hipMemcpyDeviceToHost));HIP(hipMemcpy(timestamps,times,16,hipMemcpyDeviceToHost));
    if(output!=unsigned(n)||!timestamps[0]||timestamps[1]<timestamps[0])return 3;
    if(trial>=0)printf("%s,%d,%d,%d,%s,%.3f,%.3f,%.3f,%.3f,%d,1\n",eager?"eager":"graph",n,delay,trial,side?"side_wait":"same_stream",producer_ms*1000,total_ms*1000,(timestamps[1]-timestamps[0])*1000.0/rate,std::chrono::duration<double,std::micro>(host_end-host_start).count(),pending);
   }
  }
  HIP(hipGraphExecDestroy(exec));HIP(hipGraphDestroy(graph));
 }
 HIP(hipStreamDestroy(producer));HIP(hipStreamDestroy(consumer));HIP(hipEventDestroy(begin));HIP(hipEventDestroy(end));HIP(hipEventDestroy(stop));HIP(hipFree(value));HIP(hipFree(result));HIP(hipFree(times));
}
