// Reuses the attention producer and independent CPU oracle from attention_fork_join.
// Dispatch partitioning changes only the output-head range of each launch.
#include <hip/hip_runtime.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <string>
#include <vector>
#define HIP(x) do {auto e=(x);if(e!=hipSuccess){fprintf(stderr,"HIP line %d %s: %s\n",__LINE__,#x,hipGetErrorString(e));exit(2);}}while(0)
constexpr int D=64, THREADS=256, WAVES=4;
// Exact power-of-two input scaling makes host and device inputs identical.
__host__ __device__ uint32_t mix(uint32_t x){x^=x>>16;x*=0x7feb352dU;x^=x>>15;x*=0x846ca68bU;x^=x>>16;return x;}
__host__ __device__ float input(uint32_t x){return (int(mix(x)&2047)-1024)*(1.0f/1024);}
__global__ void initialize(float* k,float* v,size_t n){size_t i=size_t(blockIdx.x)*blockDim.x+threadIdx.x;if(i<n){k[i]=input(uint32_t(i)^0x12345678U);v[i]=input(uint32_t(i)^0x87654321U);}}
__global__ void prepare(float* q,int heads,int seed){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<heads*D)q[i]=input(uint32_t(i)^uint32_t(seed*13579));}
struct Summary{float maximum,denominator,value[D];};
struct Span{unsigned long long begin,end;};
// Each CTA owns one query and one partition. Four waves scan disjoint tokens.
// The loop does real QK, stable online softmax, and a 64-component weighted V sum.
// No dummy spin, artificial shared memory reservation, or CU masking.
template<bool WIDE> __global__ void attention_part(const float* q,const float* k,const float* v,
 Summary* sums,Span* spans,int heads,int tokens,int branch,int first_head=0){
 int part=WIDE?int(blockIdx.x)/heads:branch;
 int head=WIDE?int(blockIdx.x)%heads:int(blockIdx.x)+first_head;
 int lane=threadIdx.x%D,wave=threadIdx.x/D;
 int row=part*heads+head;
 if(threadIdx.x==0)spans[row].begin=wall_clock64();
 float query=q[head*D+lane],m=-INFINITY,l=0,acc=0;
 for(int t=wave;t<tokens;t+=WAVES){
  size_t ix=(size_t(row)*tokens+t)*D+lane;
  float score=query*k[ix];
  for(int off=D/2;off;off/=2)score+=__shfl_down(score,off,D);
  score=__shfl(score,0,D)*(1.0f/8);
  float nm=fmaxf(m,score),a,b;
  if(lane==0){a=expf(m-nm);b=expf(score-nm);}else{a=0;b=0;}
  a=__shfl(a,0,D);b=__shfl(b,0,D);
  l=l*a+b;acc=acc*a+b*v[ix];m=nm;
 }
 __shared__ float maxima[WAVES],denoms[WAVES],values[WAVES][D];
 if(lane==0){maxima[wave]=m;denoms[wave]=l;}
 values[wave][lane]=acc;__syncthreads();
 if(wave==0){
  float total_m=maxima[0];for(int w=1;w<WAVES;++w)total_m=fmaxf(total_m,maxima[w]);
  float denom=0,result=0;for(int w=0;w<WAVES;++w){float s=expf(maxima[w]-total_m);denom+=denoms[w]*s;result+=values[w][lane]*s;}
  sums[row].value[lane]=result;
  if(lane==0){sums[row].maximum=total_m;sums[row].denominator=denom;}
 }
 __syncthreads();if(threadIdx.x==0)spans[row].end=wall_clock64();
}
__global__ void join(const Summary* sums,float* result,Span* spans,int heads){
 int head=blockIdx.x,lane=threadIdx.x;
 if(lane==0)spans[2*heads+head].begin=wall_clock64();
 const auto& a=sums[head];const auto& b=sums[heads+head];
 float m=fmaxf(a.maximum,b.maximum),sa=expf(a.maximum-m),sb=expf(b.maximum-m);
 result[head*D+lane]=(a.value[lane]*sa+b.value[lane]*sb)/(a.denominator*sa+b.denominator*sb);
 __syncthreads();if(lane==0)spans[2*heads+head].end=wall_clock64();
}
// Independent CPU reference scans the full concatenated token sequence in double
// precision. It does not use partition summaries or the GPU reduction algorithm.
std::vector<float> reference(int heads,int tokens,int seed){
 std::vector<float> result(size_t(heads)*D);
 for(int h=0;h<heads;++h){
  double q[D];for(int d=0;d<D;++d)q[d]=input(uint32_t(h*D+d)^uint32_t(seed*13579));
  std::vector<double> scores(size_t(tokens)*2);double maximum=-INFINITY;
  for(int p=0;p<2;++p)for(int t=0;t<tokens;++t){
   size_t ix=(size_t(p*heads+h)*tokens+t)*D;double s=0;
   for(int d=0;d<D;++d)s+=q[d]*double(input(uint32_t(ix+d)^0x12345678U));
   s*=0.125;scores[p*tokens+t]=s;maximum=std::max(maximum,s);
  }
  double denom=0,values[D]={};
  for(int p=0;p<2;++p)for(int t=0;t<tokens;++t){
   size_t ix=(size_t(p*heads+h)*tokens+t)*D;double w=std::exp(scores[p*tokens+t]-maximum);denom+=w;
   for(int d=0;d<D;++d)values[d]+=w*double(input(uint32_t(ix+d)^0x87654321U));
  }
  for(int d=0;d<D;++d)result[h*D+d]=float(values[d]/denom);
 }
 return result;
}
std::vector<float> cached_reference(int heads,int tokens,int seed,const std::string& dir){
 std::string path=dir+"/ref-h"+std::to_string(heads)+"-t"+std::to_string(tokens)+"-s"+std::to_string(seed)+".bin";
 std::vector<float> r(size_t(heads)*D);std::ifstream in(path,std::ios::binary);
 if(in){in.read(reinterpret_cast<char*>(r.data()),r.size()*sizeof(float));if(!in || in.peek()!=EOF){fprintf(stderr,"bad reference file\n");exit(3);}return r;}
 r=reference(heads,tokens,seed);std::ofstream out(path,std::ios::binary);out.write(reinterpret_cast<char*>(r.data()),r.size()*sizeof(float));if(!out)exit(3);return r;
}
int main(int argc,char** argv) {
 if(argc!=3 || !getenv("SLURM_JOB_ID")) return 2;
 int repeats=std::stoi(argv[1]); if(repeats<1) return 2;
 bool trace=getenv("GPU_NATIVE_EVENT_TRACE") && std::string(getenv("GPU_NATIVE_EVENT_TRACE"))=="1";
 int count,rate; HIP(hipGetDeviceCount(&count)); if(count!=1) return 2;
 hipDeviceProp_t prop{}; HIP(hipGetDeviceProperties(&prop,0));
 HIP(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
 if(prop.warpSize!=64 || prop.multiProcessorCount!=256) return 2;
 fprintf(stderr,"CONTROLS wait=%s relaxed=%s minimum=%s trace=%s queue_cap=%s\n",
  getenv("GPU_NATIVE_EVENT_WAIT"),getenv("GPU_NATIVE_EVENT_DIAGNOSTIC_RELAX_COST"),
  getenv("GPU_NATIVE_EVENT_DIAGNOSTIC_MIN_DISPATCHES"),getenv("GPU_NATIVE_EVENT_TRACE"),getenv("GPU_MAX_HW_QUEUES"));
 std::ifstream maps("/proc/self/maps"); for(std::string s;std::getline(maps,s);)
  if(s.find("libamdhip64")!=std::string::npos || s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
 hipStream_t main,side; HIP(hipStreamCreateWithFlags(&main,hipStreamNonBlocking)); HIP(hipStreamCreateWithFlags(&side,hipStreamNonBlocking));
 hipEvent_t start,stop,fork,done; HIP(hipEventCreate(&start)); HIP(hipEventCreate(&stop));
 HIP(hipEventCreateWithFlags(&fork,hipEventDisableTiming)); HIP(hipEventCreateWithFlags(&done,hipEventDisableTiming));
 puts("heads,tokens,launches,form,schedule,trial,total_us,host_us,submit_us,a_span_us,b_span_us,handoff_us,overlap_us,pending,max_abs_error,correct,side_ready_before_main_end,b_end_minus_a_us");
 struct Shape {int heads,tokens;};
 for(Shape shape: {Shape{256,256},Shape{256,1024},Shape{64,8192}}) {
  int heads=shape.heads,tokens=shape.tokens;
  size_t n=size_t(2)*heads*tokens*D; float *q,*k,*v,*result; Summary* sums; Span* spans;
  HIP(hipMalloc(&q,heads*D*sizeof(float))); HIP(hipMalloc(&k,n*sizeof(float))); HIP(hipMalloc(&v,n*sizeof(float)));
  HIP(hipMalloc(&result,heads*D*sizeof(float))); HIP(hipMalloc(&sums,2*heads*sizeof(Summary))); HIP(hipMalloc(&spans,3*heads*sizeof(Span)));
  initialize<<<(n+255)/256,256,0,main>>>(k,v,n); HIP(hipGetLastError()); HIP(hipStreamSynchronize(main));
  auto ref=cached_reference(heads,tokens,1,argv[2]);
  std::vector<float> actual(heads*D); std::vector<Span> times(3*heads);
  for(int launches:{1,4,16,256}) {
   if(heads==64 && launches!=1)continue;
   for(bool captured:{false,true}) for(int schedule:{0,1,2}) {
    if(schedule==2 && launches!=1)continue;
    const char* name=schedule==0?"serial":schedule==1?"parallel":"wide";
    int pending=-1;
    auto branch=[&](int part,hipStream_t stream) {
     for(int i=0;i<launches;++i) {
      int first=i*heads/launches, last=(i+1)*heads/launches;
      attention_part<false><<<last-first,THREADS,0,stream>>>(q,k,v,sums,spans,heads,tokens,part,first);
     }
    };
    auto enqueue=[&]() {
     prepare<<<(heads*D+255)/256,256,0,main>>>(q,heads,1);
     if(schedule==0) {branch(0,main);branch(1,main);}
     else if(schedule==1) {
      HIP(hipEventRecord(fork,main)); HIP(hipStreamWaitEvent(side,fork,0));
      branch(1,side); HIP(hipEventRecord(done,side)); branch(0,main);
      if(!captured) {auto status=hipEventQuery(done);if(status!=hipSuccess&&status!=hipErrorNotReady)HIP(status);pending=status==hipErrorNotReady;}
      HIP(hipStreamWaitEvent(main,done,0));
     } else attention_part<true><<<2*heads,THREADS,0,main>>>(q,k,v,sums,spans,heads,tokens,0);
     join<<<heads,D,0,main>>>(sums,result,spans,heads); HIP(hipGetLastError());
    };
    hipGraph_t graph{}; hipGraphExec_t executable{};
    // Resolve module/workspace startup before capture and measured trials.
    enqueue(); HIP(hipDeviceSynchronize());
    if(captured) {
     HIP(hipStreamBeginCapture(main,hipStreamCaptureModeGlobal)); enqueue();
     HIP(hipStreamEndCapture(main,&graph)); HIP(hipGraphInstantiate(&executable,graph,nullptr,nullptr,0));
     size_t nodes=0; HIP(hipGraphGetNodes(graph,nullptr,&nodes));
     fprintf(stderr,"GRAPH heads=%d tokens=%d launches=%d schedule=%s nodes=%zu\n",heads,tokens,launches,name,nodes);
    }
    for(int trial=trace?0:-2;trial<repeats;++trial) {
     HIP(hipMemsetAsync(result,0xff,heads*D*sizeof(float),main)); HIP(hipMemsetAsync(sums,0xff,2*heads*sizeof(Summary),main));
     HIP(hipMemsetAsync(spans,0,3*heads*sizeof(Span),main)); HIP(hipStreamSynchronize(main));
     if(trace) {fprintf(stderr,"CELL_BEGIN heads=%d tokens=%d launches=%d form=%s schedule=%s trial=%d\n",heads,tokens,launches,captured?"graph":"eager",name,trial);fflush(stderr);}
     auto h0=std::chrono::steady_clock::now(); HIP(hipEventRecord(start,main));
     if(captured) HIP(hipGraphLaunch(executable,main)); else enqueue();
     HIP(hipEventRecord(stop,main)); auto h1=std::chrono::steady_clock::now(); HIP(hipEventSynchronize(stop)); auto h2=std::chrono::steady_clock::now();
     float ms; HIP(hipEventElapsedTime(&ms,start,stop));
     HIP(hipMemcpy(actual.data(),result,actual.size()*sizeof(float),hipMemcpyDeviceToHost)); HIP(hipMemcpy(times.data(),spans,times.size()*sizeof(Span),hipMemcpyDeviceToHost));
     double error=0; for(size_t i=0;i<actual.size();++i) {if(!std::isfinite(actual[i]))return 3;error=std::max(error,std::abs(double(actual[i])-ref[i]));}
     if(error>2e-5) {fprintf(stderr,"bad result error=%g\n",error);return 3;}
     unsigned long long lo[3]={~0ULL,~0ULL,~0ULL},hi[3]={0,0,0};
     for(int p=0;p<3;++p)for(int h=0;h<heads;++h){auto x=times[p*heads+h];if(!x.begin||x.end<=x.begin)return 3;lo[p]=std::min(lo[p],x.begin);hi[p]=std::max(hi[p],x.end);}
     double scale=1000.0/rate, gap=(double(lo[2])-double(std::max(hi[0],hi[1])))*scale;
     double overlap=std::max(0.0,double(std::min(hi[0],hi[1]))-double(std::max(lo[0],lo[1])))*scale;
     if(gap < -1 || (schedule==0 && overlap>1))return 3;
     if(trial>=0) printf("%d,%d,%d,%s,%s,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%.9g,1,%d,%.3f\n",heads,tokens,launches,captured?"graph":"eager",name,trial,ms*1000,
       std::chrono::duration<double,std::micro>(h2-h0).count(),std::chrono::duration<double,std::micro>(h1-h0).count(),(hi[0]-lo[0])*scale,(hi[1]-lo[1])*scale,gap,overlap,pending,error,int(hi[1]<=hi[0]),(double(hi[1])-double(hi[0]))*scale);
     if(trace) {fprintf(stderr,"CELL_END\n");fflush(stderr);}
    }
    if(executable)HIP(hipGraphExecDestroy(executable));if(graph)HIP(hipGraphDestroy(graph));
   }
  }
  HIP(hipStreamSynchronize(side)); HIP(hipFree(q));HIP(hipFree(k));HIP(hipFree(v));HIP(hipFree(result));HIP(hipFree(sums));HIP(hipFree(spans));
 }
 HIP(hipEventDestroy(start));HIP(hipEventDestroy(stop));HIP(hipEventDestroy(fork));HIP(hipEventDestroy(done));HIP(hipStreamDestroy(main));HIP(hipStreamDestroy(side));
}
