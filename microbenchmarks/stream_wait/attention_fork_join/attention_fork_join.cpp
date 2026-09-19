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
 Summary* sums,Span* spans,int heads,int tokens,int branch){
 int part=WIDE?int(blockIdx.x)/heads:branch;
 int head=WIDE?int(blockIdx.x)%heads:int(blockIdx.x);
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
int main(int argc,char** argv){
 if(argc!=5 || !getenv("SLURM_JOB_ID")){fprintf(stderr,"usage: benchmark tokens repeats reference_dir head_divisor(0=all)\n");return 2;}
 int tokens=std::stoi(argv[1]),repeats=std::stoi(argv[2]),selected=std::stoi(argv[4]);
 if(tokens<4 || tokens%4 || repeats<4 || (selected!=0&&selected!=1&&selected!=2&&selected!=4))return 2;
 int count=0;HIP(hipGetDeviceCount(&count));if(count!=1)return 2;
 hipDeviceProp_t prop{};HIP(hipGetDeviceProperties(&prop,0));if(prop.warpSize!=64 || !prop.concurrentKernels)return 2;
 int rate=0;HIP(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
 hipFuncAttributes attr{};HIP(hipFuncGetAttributes(&attr,reinterpret_cast<const void*>(attention_part<false>)));int active=0;
 HIP(hipOccupancyMaxActiveBlocksPerMultiprocessor(&active,attention_part<false>,THREADS,0));
 fprintf(stderr,"DEVICE name=%s arch=%s CUs=%d wave=%d concurrent=%d rate_khz=%d registers=%d shared=%zu max_blocks_per_CU=%d\n",prop.name,prop.gcnArchName,prop.multiProcessorCount,prop.warpSize,prop.concurrentKernels,rate,attr.numRegs,attr.sharedSizeBytes,active);
 std::ifstream maps("/proc/self/maps");for(std::string line;std::getline(maps,line);)if(line.find("libamdhip64")!=std::string::npos||line.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",line.c_str());
 fprintf(stderr,"RUNTIME mode=%s native_wait=%s\n",getenv("AFJ_RUNTIME_MODE")?getenv("AFJ_RUNTIME_MODE"):"unset",getenv("GPU_NATIVE_EVENT_WAIT")?getenv("GPU_NATIVE_EVENT_WAIT"):"unset");
 hipStream_t main,side;HIP(hipStreamCreateWithFlags(&main,hipStreamNonBlocking));HIP(hipStreamCreateWithFlags(&side,hipStreamNonBlocking));
 hipEvent_t start,stop,fork,done;HIP(hipEventCreate(&start));HIP(hipEventCreate(&stop));HIP(hipEventCreateWithFlags(&fork,hipEventDisableTiming));HIP(hipEventCreateWithFlags(&done,hipEventDisableTiming));
 puts("heads,tokens_per_partition,trial,seed,schedule,total_us,host_us,a_span_us,b_span_us,overlap_us,span_union_us,join_pending,max_abs_error,correct,a_start_offset_us,b_start_offset_us,join_after_branches_us,join_span_us");
 for(int divisor:{4,2,1}){
  if(selected && divisor!=selected)continue;
  int heads=std::max(1,prop.multiProcessorCount/divisor);
  size_t n=size_t(2)*heads*tokens*D;float *q,*k,*v,*result;Summary* sums;Span* spans;
  HIP(hipMalloc(&q,heads*D*sizeof(float)));HIP(hipMalloc(&k,n*sizeof(float)));HIP(hipMalloc(&v,n*sizeof(float)));HIP(hipMalloc(&result,heads*D*sizeof(float)));HIP(hipMalloc(&sums,2*heads*sizeof(Summary)));HIP(hipMalloc(&spans,3*heads*sizeof(Span)));
  initialize<<<(n+255)/256,256,0,main>>>(k,v,n);HIP(hipGetLastError());HIP(hipStreamSynchronize(main));
  std::vector<std::vector<float>> refs;for(int seed=1;seed<=4;++seed)refs.push_back(cached_reference(heads,tokens,seed,argv[3]));
  std::vector<float> actual(heads*D);std::vector<Span> times(3*heads);
  const char* names[]={"serial","parallel","wide"};
  for(int trial=-4;trial<repeats;++trial)for(int order=0;order<3;++order){
   int schedule=(order+trial+6)%3,seed=(trial+4)%4+1;
   // Poison output and all intermediates; errors cannot be hidden by a previous trial.
   HIP(hipMemsetAsync(result,0xff,heads*D*sizeof(float),main));HIP(hipMemsetAsync(sums,0xff,2*heads*sizeof(Summary),main));HIP(hipMemsetAsync(spans,0,3*heads*sizeof(Span),main));HIP(hipStreamSynchronize(main));
   auto host_start=std::chrono::steady_clock::now();
   HIP(hipEventRecord(start,main));prepare<<<(heads*D+255)/256,256,0,main>>>(q,heads,seed);
   int pending=-1;
   if(schedule==0){
    attention_part<false><<<heads,THREADS,0,main>>>(q,k,v,sums,spans,heads,tokens,0);
    attention_part<false><<<heads,THREADS,0,main>>>(q,k,v,sums,spans,heads,tokens,1);
   }else if(schedule==1){
    HIP(hipEventRecord(fork,main));HIP(hipStreamWaitEvent(side,fork,0));
    attention_part<false><<<heads,THREADS,0,side>>>(q,k,v,sums,spans,heads,tokens,1);
    HIP(hipEventRecord(done,side));
    attention_part<false><<<heads,THREADS,0,main>>>(q,k,v,sums,spans,heads,tokens,0);
    // Query is outside the GPU timeline; record whether the dependency was pending
    // when the host submitted it. The event wait always remains in the schedule.
    auto status=hipEventQuery(done);if(status!=hipSuccess&&status!=hipErrorNotReady)HIP(status);pending=status==hipErrorNotReady;
    HIP(hipStreamWaitEvent(main,done,0));
   }else attention_part<true><<<2*heads,THREADS,0,main>>>(q,k,v,sums,spans,heads,tokens,0);
   join<<<heads,D,0,main>>>(sums,result,spans,heads);HIP(hipGetLastError());HIP(hipEventRecord(stop,main));HIP(hipEventSynchronize(stop));
   auto host_stop=std::chrono::steady_clock::now();float elapsed;HIP(hipEventElapsedTime(&elapsed,start,stop));
   HIP(hipMemcpy(actual.data(),result,actual.size()*sizeof(float),hipMemcpyDeviceToHost));HIP(hipMemcpy(times.data(),spans,times.size()*sizeof(Span),hipMemcpyDeviceToHost));
   double error=0;for(size_t i=0;i<actual.size();++i){if(!std::isfinite(actual[i])){fprintf(stderr,"nonfinite output\n");return 4;}error=std::max(error,std::abs(double(actual[i])-refs[seed-1][i]));}
   if(error>2e-5){fprintf(stderr,"reference failed heads=%d schedule=%s seed=%d error=%.9g\n",heads,names[schedule],seed,error);return 4;}
   unsigned long long lo[2]={~0ULL,~0ULL},hi[2]={0,0};
   for(int p=0;p<2;++p)for(int h=0;h<heads;++h){auto x=times[p*heads+h];if(!x.begin||x.end<=x.begin)return 5;lo[p]=std::min(lo[p],x.begin);hi[p]=std::max(hi[p],x.end);}
   double scale=1000.0/rate,a=(hi[0]-lo[0])*scale,b=(hi[1]-lo[1])*scale;
   double overlap=std::max(0.0,double(std::min(hi[0],hi[1]))-double(std::max(lo[0],lo[1])))*scale;
   double united=(std::max(hi[0],hi[1])-std::min(lo[0],lo[1]))*scale;
   if(schedule==0 && overlap>1){fprintf(stderr,"serial timestamps overlap\n");return 5;}
   unsigned long long join_lo=~0ULL,join_hi=0;
   for(int h=0;h<heads;++h){auto x=times[2*heads+h];if(!x.begin||x.end<=x.begin)return 5;join_lo=std::min(join_lo,x.begin);join_hi=std::max(join_hi,x.end);}
   double a_offset=(lo[0]-std::min(lo[0],lo[1]))*scale,b_offset=(lo[1]-std::min(lo[0],lo[1]))*scale;
   double join_gap=(double(join_lo)-double(std::max(hi[0],hi[1])))*scale;
   if(join_gap < -1){fprintf(stderr,"join began before branch completion\n");return 5;}
   if(trial>=0)printf("%d,%d,%d,%d,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%.9g,1,%.3f,%.3f,%.3f,%.3f\n",heads,tokens,trial,seed,names[schedule],elapsed*1000,std::chrono::duration<double,std::micro>(host_stop-host_start).count(),a,b,overlap,united,pending,error,a_offset,b_offset,join_gap,(join_hi-join_lo)*scale);
  }
  HIP(hipStreamSynchronize(side));HIP(hipFree(q));HIP(hipFree(k));HIP(hipFree(v));HIP(hipFree(result));HIP(hipFree(sums));HIP(hipFree(spans));
 }
 HIP(hipEventDestroy(start));HIP(hipEventDestroy(stop));HIP(hipEventDestroy(fork));HIP(hipEventDestroy(done));HIP(hipStreamDestroy(main));HIP(hipStreamDestroy(side));
}
