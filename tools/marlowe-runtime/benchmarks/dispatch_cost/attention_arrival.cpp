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
#include <sstream>
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
// Timer filler controls wait arrival only. It is not the useful producer or a
// claim about representative HiSparse compute; the producer remains real attention.
__global__ void arrival_filler(unsigned long long ticks,unsigned long long* ended) {
 auto start=wall_clock64();while(wall_clock64()-start<ticks){} *ended=wall_clock64();
}
int main(int argc,char** argv) {
 if(argc!=3 || !getenv("SLURM_JOB_ID"))return 2;
 int repeats=std::stoi(argv[1]);if(repeats<1)return 2;
 bool trace=getenv("GPU_NATIVE_EVENT_TRACE")&&std::string(getenv("GPU_NATIVE_EVENT_TRACE"))=="1";
 std::vector<int> launch_counts{1,16,256};
 if(const char* configured=getenv("ARRIVAL_LAUNCHES")) {
  launch_counts.clear();std::istringstream input(configured);std::string token;
  while(std::getline(input,token,',')) {
   int n=std::stoi(token);
   if(n<1 || n>256 || (n&(n-1)) || std::find(launch_counts.begin(),launch_counts.end(),n)!=launch_counts.end())return 2;
   launch_counts.push_back(n);
  }
  if(launch_counts.empty())return 2;
 }
 fprintf(stderr,"WORKLOAD launches=");for(size_t i=0;i<launch_counts.size();++i)fprintf(stderr,"%s%d",i?",":"",launch_counts[i]);fprintf(stderr,"\n");
 int count,rate;HIP(hipGetDeviceCount(&count));if(count!=1)return 2;HIP(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
 fprintf(stderr,"CONTROLS wait=%s relaxed=%s minimum=%s trace=%s queue_cap=%s\n",getenv("GPU_NATIVE_EVENT_WAIT"),getenv("GPU_NATIVE_EVENT_DIAGNOSTIC_RELAX_COST"),getenv("GPU_NATIVE_EVENT_DIAGNOSTIC_MIN_DISPATCHES"),getenv("GPU_NATIVE_EVENT_TRACE"),getenv("GPU_MAX_HW_QUEUES"));
 std::ifstream maps("/proc/self/maps");for(std::string s;std::getline(maps,s);)
  if(s.find("libamdhip64")!=std::string::npos||s.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",s.c_str());
 hipStream_t producer,consumer;HIP(hipStreamCreateWithFlags(&producer,hipStreamNonBlocking));HIP(hipStreamCreateWithFlags(&consumer,hipStreamNonBlocking));
 hipEvent_t begin,end,stop;HIP(hipEventCreate(&begin));HIP(hipEventCreate(&end));HIP(hipEventCreate(&stop));
 puts("heads,tokens,launches,form,schedule,trial,total_us,producer_us,host_us,submit_us,b_span_us,handoff_us,pending,ready_before_wait,max_abs_error,correct,filler_us,prefix_end_minus_b_us");
 struct Shape{int heads,tokens;};
 for(Shape sh:{Shape{256,256},Shape{256,1024},Shape{64,8192}}){
  int heads=sh.heads,tokens=sh.tokens;size_t n=size_t(2)*heads*tokens*D;
  float *q,*k,*v,*result;Summary* sums;Span* spans;unsigned long long* prefix;
  HIP(hipMalloc(&q,heads*D*sizeof(float)));HIP(hipMalloc(&k,n*sizeof(float)));HIP(hipMalloc(&v,n*sizeof(float)));HIP(hipMalloc(&result,heads*D*sizeof(float)));HIP(hipMalloc(&sums,2*heads*sizeof(Summary)));HIP(hipMalloc(&spans,3*heads*sizeof(Span)));HIP(hipMalloc(&prefix,8));
  initialize<<<(n+255)/256,256,0,producer>>>(k,v,n);prepare<<<(heads*D+255)/256,256,0,producer>>>(q,heads,1);
  // Unchanging partition0 is computed once outside all measured intervals.
  attention_part<false><<<heads,THREADS,0,producer>>>(q,k,v,sums,spans,heads,tokens,0);HIP(hipGetLastError());HIP(hipStreamSynchronize(producer));
  auto ref=cached_reference(heads,tokens,1,argv[2]);std::vector<float> actual(heads*D);std::vector<Span> times(3*heads);
  for(int launches:launch_counts){
   if(heads==64&&launches!=1)continue;
   auto work=[&](){for(int i=0;i<launches;++i){int first=i*heads/launches,last=(i+1)*heads/launches;attention_part<false><<<last-first,THREADS,0,producer>>>(q,k,v,sums,spans,heads,tokens,1,first);}HIP(hipGetLastError());};
   hipGraph_t graph{};hipGraphExec_t executable{};work();HIP(hipStreamSynchronize(producer));
   HIP(hipStreamBeginCapture(producer,hipStreamCaptureModeGlobal));work();HIP(hipStreamEndCapture(producer,&graph));HIP(hipGraphInstantiate(&executable,graph,nullptr,nullptr,0));
   for(bool captured:{false,true}){
    auto launch=[&](){if(captured)HIP(hipGraphLaunch(executable,producer));else work();};
    // First stock process freezes a prefix length for every runtime/round. The
    // prefix is never retuned per policy; realized device readiness is reported.
    std::string delay_path=std::string(argv[2])+"/delay-h"+std::to_string(heads)+"-t"+std::to_string(tokens)+"-k"+std::to_string(launches)+(captured?"-graph.txt":"-eager.txt");
    unsigned long long filler_ticks=0;
    std::ifstream delay_in(delay_path);
    if(delay_in) {delay_in>>filler_ticks;if(!delay_in||!filler_ticks)return 3;}
    else {
     if(!getenv("ARRIVAL_CALIBRATE")||std::string(getenv("ARRIVAL_CALIBRATE"))!="1")return 3;
     HIP(hipEventRecord(begin,producer));launch();HIP(hipEventRecord(end,producer));HIP(hipEventSynchronize(end));float isolated_ms;HIP(hipEventElapsedTime(&isolated_ms,begin,end));
     filler_ticks=static_cast<unsigned long long>((isolated_ms*1200+200)*rate/1000);
     std::ofstream delay_out(delay_path);delay_out<<filler_ticks<<"\n";if(!delay_out)return 3;
    }
    const double filler_us=filler_ticks*1000.0/rate;
    for(int trial=trace?0:-2;trial<repeats;++trial)for(int order=0;order<4;++order){
     int mode=(order+trial+4)%4;const char* names[]={"alone","early","delayed","cpu_ready"};
     HIP(hipMemsetAsync(result,0xff,heads*D*sizeof(float),producer));HIP(hipMemsetAsync(sums+heads,0xff,heads*sizeof(Summary),producer));HIP(hipMemsetAsync(spans+heads,0,2*heads*sizeof(Span),producer));HIP(hipMemsetAsync(prefix,0,8,producer));HIP(hipStreamSynchronize(producer));
     if(trace){fprintf(stderr,"CELL_BEGIN heads=%d tokens=%d launches=%d form=%s schedule=%s trial=%d\n",heads,tokens,launches,captured?"producer_graph":"eager",names[mode],trial);fflush(stderr);}
     auto h0=std::chrono::steady_clock::now();
     if(mode==2)arrival_filler<<<1,1,0,consumer>>>(filler_ticks,prefix);
     HIP(hipEventRecord(begin,producer));launch();HIP(hipEventRecord(end,producer));
     if(mode==3)HIP(hipEventSynchronize(end));
     auto status=hipEventQuery(end);if(status!=hipSuccess&&status!=hipErrorNotReady)HIP(status);int pending=status==hipErrorNotReady;
     auto target=mode?consumer:producer;if(mode)HIP(hipStreamWaitEvent(consumer,end,0));
     join<<<heads,D,0,target>>>(sums,result,spans,heads);HIP(hipGetLastError());HIP(hipEventRecord(stop,target));auto h1=std::chrono::steady_clock::now();HIP(hipEventSynchronize(stop));auto h2=std::chrono::steady_clock::now();
     float total_ms,producer_ms;HIP(hipEventElapsedTime(&total_ms,begin,stop));HIP(hipEventElapsedTime(&producer_ms,begin,end));
     HIP(hipMemcpy(actual.data(),result,actual.size()*sizeof(float),hipMemcpyDeviceToHost));HIP(hipMemcpy(times.data(),spans,times.size()*sizeof(Span),hipMemcpyDeviceToHost));unsigned long long prefix_end;HIP(hipMemcpy(&prefix_end,prefix,8,hipMemcpyDeviceToHost));
     double err=0;for(size_t i=0;i<actual.size();++i){if(!std::isfinite(actual[i]))return 3;err=std::max(err,std::abs(double(actual[i])-ref[i]));}if(err>2e-5)return 3;
     unsigned long long lo=~0ULL,hi=0,joined=~0ULL;for(int h=0;h<heads;++h){auto x=times[heads+h];auto j=times[2*heads+h];if(!x.begin||x.end<=x.begin||!j.begin)return 3;lo=std::min(lo,x.begin);hi=std::max(hi,x.end);joined=std::min(joined,j.begin);}
     double scale=1000.0/rate,gap=(double(joined)-double(hi))*scale;if(gap < -1)return 3;
     int ready=mode==3?1:mode==2?int(prefix_end>=hi):-1;
     if(mode==3&&pending)return 3;
     if(trial>=0)printf("%d,%d,%d,%s,%s,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%d,%.9g,1,%.3f,%.3f\n",heads,tokens,launches,captured?"producer_graph":"eager",names[mode],trial,total_ms*1000,producer_ms*1000,std::chrono::duration<double,std::micro>(h2-h0).count(),std::chrono::duration<double,std::micro>(h1-h0).count(),(hi-lo)*scale,gap,pending,ready,err,mode==2?filler_us:0,mode==2?(double(prefix_end)-double(hi))*scale:0);
     if(trace){fprintf(stderr,"CELL_END\n");fflush(stderr);}
    }
   }
   HIP(hipGraphExecDestroy(executable));HIP(hipGraphDestroy(graph));
  }
  HIP(hipFree(q));HIP(hipFree(k));HIP(hipFree(v));HIP(hipFree(result));HIP(hipFree(sums));HIP(hipFree(spans));HIP(hipFree(prefix));
 }
 HIP(hipEventDestroy(begin));HIP(hipEventDestroy(end));HIP(hipEventDestroy(stop));HIP(hipStreamDestroy(producer));HIP(hipStreamDestroy(consumer));
}
