// Deterministic late handoff: observe a GPU-written checkpoint, then wait on its tail.
#include <hip/hip_runtime.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#define HIP(x) do{auto e=(x);if(e!=hipSuccess){fprintf(stderr,"line%d %s\n",__LINE__,hipGetErrorString(e));exit(2);}}while(0)
__global__ void increment(unsigned* p){++*p;}
__global__ void checkpoint(unsigned* flag){*flag=1;__threadfence_system();}
__global__ void stamp(unsigned long long* t,int i){t[i]=wall_clock64();}
__global__ void consume(const unsigned* value,unsigned* out,unsigned long long* t){*out=*value;t[1]=wall_clock64();}
int main(int argc,char** argv){
 if(argc!=2||!getenv("SLURM_JOB_ID"))return 2;int repeats=std::stoi(argv[1]),count,rate;
 HIP(hipGetDeviceCount(&count));if(count!=1)return 2;HIP(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
 std::ifstream maps("/proc/self/maps");for(std::string s;std::getline(maps,s);)if(s.find("libamdhip64")!=std::string::npos||s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
 hipStream_t p,c;HIP(hipStreamCreateWithFlags(&p,hipStreamNonBlocking));HIP(hipStreamCreateWithFlags(&c,hipStreamNonBlocking));
 hipEvent_t begin,end,stop;HIP(hipEventCreate(&begin));HIP(hipEventCreate(&end));HIP(hipEventCreate(&stop));
 unsigned *flag,*value,*out;unsigned long long* times;HIP(hipHostMalloc(&flag,4,hipHostMallocMapped|hipHostMallocCoherent));HIP(hipMalloc(&value,4));HIP(hipMalloc(&out,4));HIP(hipMalloc(&times,16));
 puts("kernels,tail,trial,schedule,producer_us,total_us,resume_gap_us,pending,correct");
 for(int n:{384,512,1024,2048})for(int tail:{4,16,64}){
  hipGraph_t graph;hipGraphExec_t exec;HIP(hipStreamBeginCapture(p,hipStreamCaptureModeGlobal));
  for(int i=0;i<n-tail;++i)increment<<<1,1,0,p>>>(value);checkpoint<<<1,1,0,p>>>(flag);
  for(int i=0;i<tail;++i)increment<<<1,1,0,p>>>(value);stamp<<<1,1,0,p>>>(times,0);
  HIP(hipStreamEndCapture(p,&graph));HIP(hipGraphInstantiate(&exec,graph,nullptr,nullptr,0));
  for(int trial=-2;trial<repeats;++trial)for(int order=0;order<2;++order){
   int side=(order+trial+2)%2;__atomic_store_n(flag,0u,__ATOMIC_RELEASE);HIP(hipMemsetAsync(value,0,4,p));HIP(hipMemsetAsync(out,0xff,4,p));HIP(hipStreamSynchronize(p));
   HIP(hipEventRecord(begin,p));HIP(hipGraphLaunch(exec,p));HIP(hipEventRecord(end,p));
   auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(1);
   while(!__atomic_load_n(flag,__ATOMIC_ACQUIRE)){if(std::chrono::steady_clock::now()>deadline)return 3;}
   auto state=hipEventQuery(end);if(state!=hipSuccess&&state!=hipErrorNotReady)HIP(state);bool pending=state==hipErrorNotReady;
   hipStream_t target=side?c:p;if(side)HIP(hipStreamWaitEvent(c,end,0));consume<<<1,1,0,target>>>(value,out,times);HIP(hipGetLastError());HIP(hipEventRecord(stop,target));HIP(hipEventSynchronize(stop));
   float ms,total;HIP(hipEventElapsedTime(&ms,begin,end));HIP(hipEventElapsedTime(&total,begin,stop));unsigned got;unsigned long long t[2];HIP(hipMemcpy(&got,out,4,hipMemcpyDeviceToHost));HIP(hipMemcpy(t,times,16,hipMemcpyDeviceToHost));if(got!=unsigned(n)||t[1]<t[0])return 4;
   if(trial>=0)printf("%d,%d,%d,%s,%.3f,%.3f,%.3f,%d,1\n",n,tail,trial,side?"side_wait":"same_stream",ms*1000,total*1000,(t[1]-t[0])*1000.0/rate,pending);
  }
  HIP(hipGraphExecDestroy(exec));HIP(hipGraphDestroy(graph));
 }
 HIP(hipEventDestroy(begin));HIP(hipEventDestroy(end));HIP(hipEventDestroy(stop));HIP(hipStreamDestroy(p));HIP(hipStreamDestroy(c));HIP(hipFree(value));HIP(hipFree(out));HIP(hipFree(times));HIP(hipHostFree(flag));
}
