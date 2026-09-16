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
struct Bounds{int offset[5];};
template<bool WIDE> __global__ void attention_part(const float* q,const float* k,const float* v,
 Summary* sums,Span* spans,int heads,int total_tokens,int branches,int stage,int stage_tokens,Bounds bounds,int branch){
 int part=WIDE?int(blockIdx.x)/heads:branch;
 int head=WIDE?int(blockIdx.x)%heads:int(blockIdx.x);
 int lane=threadIdx.x%D,wave=threadIdx.x/D;
 int row=part*heads+head,span_row=(stage*(branches+1)+part)*heads+head;
 if(threadIdx.x==0)spans[span_row].begin=wall_clock64();
 float query=q[head*D+lane],m=-INFINITY,l=0,acc=0;
 for(int t=bounds.offset[part]+wave;t<bounds.offset[part+1];t+=WAVES){
  size_t ix=(size_t(head)*total_tokens+stage*stage_tokens+t)*D+lane;
  float score=query*k[ix];
  for(int off=D/2;off;off/=2)score+=__shfl_down(score,off,D);
  score=__shfl(score,0,D)*0.125f;
  float nm=fmaxf(m,score),a=0,b=0;
  if(lane==0){a=expf(m-nm);b=expf(score-nm);}
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
 __syncthreads();if(threadIdx.x==0)spans[span_row].end=wall_clock64();
}
// The next stage genuinely consumes all branch results. It cannot execute early.
__global__ void join_update(const Summary* sums,float* q,Span* spans,int heads,int branches,int stage){
 int h=blockIdx.x,d=threadIdx.x,row=(stage*(branches+1)+branches)*heads+h;
 if(d==0)spans[row].begin=wall_clock64();
 float m=-INFINITY;for(int b=0;b<branches;++b)m=fmaxf(m,sums[b*heads+h].maximum);
 float l=0,z=0;for(int b=0;b<branches;++b){const auto& s=sums[b*heads+h];float a=expf(s.maximum-m);l+=s.denominator*a;z+=s.value[d]*a;}
 q[h*D+d]=fmaf(0.125f,z/l,q[h*D+d]);
 __syncthreads();if(d==0)spans[row].end=wall_clock64();
}
std::vector<float> reference(int heads,int total,int stages,int seed){
 std::vector<float> q(size_t(heads)*D);for(size_t i=0;i<q.size();++i)q[i]=input(uint32_t(i)^uint32_t(seed*13579));
 int length=total/stages;std::vector<double> scores(length);
 for(int h=0;h<heads;++h)for(int st=0;st<stages;++st){
  double m=-INFINITY;
  for(int t=0;t<length;++t){size_t ix=(size_t(h)*total+st*length+t)*D;double dot=0;
   for(int d=0;d<D;++d)dot+=double(q[h*D+d])*input(uint32_t(ix+d)^0x12345678U);
   scores[t]=dot*0.125;m=std::max(m,scores[t]);
  }
  double l=0,z[D]={};for(int t=0;t<length;++t){size_t ix=(size_t(h)*total+st*length+t)*D;double w=std::exp(scores[t]-m);l+=w;
   for(int d=0;d<D;++d)z[d]+=w*input(uint32_t(ix+d)^0x87654321U);
  }
  for(int d=0;d<D;++d)q[h*D+d]=std::fma(0.125f,float(z[d]/l),q[h*D+d]);
 }
 return q;
}
std::vector<float> cached_reference(int heads,int total,int stages,int seed,const std::string& dir){
 std::string path=dir+"/ref-h"+std::to_string(heads)+"-t"+std::to_string(total)+"-st"+std::to_string(stages)+"-s"+std::to_string(seed)+".bin";
 std::vector<float> r(size_t(heads)*D);std::ifstream in(path,std::ios::binary);
 if(in){in.read(reinterpret_cast<char*>(r.data()),r.size()*sizeof(float));if(!in||in.peek()!=EOF)exit(3);return r;}
 r=reference(heads,total,stages,seed);std::ofstream out(path,std::ios::binary);out.write(reinterpret_cast<char*>(r.data()),r.size()*sizeof(float));if(!out)exit(3);return r;
}
struct Config{const char* name;int heads,total,stages;bool skew;};
int main(int argc,char** argv){
 if(argc!=4||!getenv("SLURM_JOB_ID")){fprintf(stderr,"usage: binary repeats reference_dir quick(0/1)\n");return 2;}
 int repeats=std::stoi(argv[1]);bool quick=std::stoi(argv[3]);if(repeats<4)return 2;
 int count;HIP(hipGetDeviceCount(&count));if(count!=1)return 2;hipDeviceProp_t prop{};HIP(hipGetDeviceProperties(&prop,0));
 if(prop.warpSize!=64||!prop.concurrentKernels)return 2;
 int rate;HIP(hipDeviceGetAttribute(&rate,hipDeviceAttributeWallClockRate,0));
 hipFuncAttributes attr{};HIP(hipFuncGetAttributes(&attr,reinterpret_cast<const void*>(attention_part<false>)));int capacity;
 HIP(hipOccupancyMaxActiveBlocksPerMultiprocessor(&capacity,attention_part<false>,THREADS,0));
 fprintf(stderr,"DEVICE CUs=%d rate_khz=%d registers=%d shared=%zu max_blocks_per_CU=%d\n",prop.multiProcessorCount,rate,attr.numRegs,attr.sharedSizeBytes,capacity);
 std::ifstream maps("/proc/self/maps");for(std::string line;std::getline(maps,line);)if(line.find("libamdhip64")!=std::string::npos||line.find("libhsa-runtime64")!=std::string::npos)fprintf(stderr,"LIBRARY %s\n",line.c_str());
 fprintf(stderr,"RUNTIME mode=%s native_wait=%s\n",getenv("ASC_RUNTIME_MODE"),getenv("GPU_NATIVE_EVENT_WAIT"));
 hipStream_t streams[4];hipEvent_t ready,done[4],start,stop;
 for(int b=0;b<4;++b){HIP(hipStreamCreateWithFlags(&streams[b],hipStreamNonBlocking));HIP(hipEventCreateWithFlags(&done[b],hipEventDisableTiming));}
 HIP(hipEventCreateWithFlags(&ready,hipEventDisableTiming));HIP(hipEventCreate(&start));HIP(hipEventCreate(&stop));
 std::vector<Config> configs={{"balanced-long",128,16384,1,false},{"uneven-long",128,16384,1,true},{"balanced-16",128,16384,16,false},{"uneven-16",128,16384,16,true},{"balanced-64",128,16384,64,false},{"uneven-64",128,16384,64,true},{"occupied",2048,4096,1,false}};
 if(quick)configs={{"balanced-long",128,16384,1,false},{"uneven-16",128,16384,16,true}};
 if(const char* chosen=getenv("ASC_CONFIG")){configs.erase(std::remove_if(configs.begin(),configs.end(),[&](const Config& c){return std::string(c.name)!=chosen;}),configs.end());if(configs.empty())return 2;}
 puts("config,heads,total_tokens,stages,branches,trial,seed,schedule,total_us,host_us,branch_span_sum_us,branch_union_sum_us,overlap_saved_us,join_gap_sum_us,join_span_sum_us,branch_start_skew_sum_us,continuation_gap_sum_us,max_abs_error,correct");
 for(const auto& cfg:configs){
  int heads=cfg.heads,total=cfg.total,stages=cfg.stages,stage_tokens=total/stages;
  size_t n=size_t(heads)*total*D;float *q,*k,*v;Summary* sums;Span* spans;
  HIP(hipMalloc(&q,heads*D*sizeof(float)));HIP(hipMalloc(&k,n*sizeof(float)));HIP(hipMalloc(&v,n*sizeof(float)));HIP(hipMalloc(&sums,4*heads*sizeof(Summary)));HIP(hipMalloc(&spans,stages*5*heads*sizeof(Span)));
  initialize<<<(n+255)/256,256,0,streams[0]>>>(k,v,n);HIP(hipGetLastError());HIP(hipStreamSynchronize(streams[0]));
  std::vector<std::vector<float>> refs;for(int seed=1;seed<=2;++seed)refs.push_back(cached_reference(heads,total,stages,seed,argv[2]));
  for(int branches:{2,4}){
   Bounds bounds{};bounds.offset[0]=0;bounds.offset[branches]=stage_tokens;
   if(cfg.skew){bounds.offset[1]=stage_tokens*7/8;for(int b=2;b<branches;++b)bounds.offset[b]=bounds.offset[1]+(stage_tokens-bounds.offset[1])*(b-1)/(branches-1);}
   else for(int b=1;b<branches;++b)bounds.offset[b]=stage_tokens*b/branches;
   for(int b=0;b<branches;++b)if(bounds.offset[b+1]-bounds.offset[b]<4)return 2;
   std::vector<float> actual(heads*D);std::vector<Span> times(stages*(branches+1)*heads);const char* names[]={"serial","parallel","wide"};
   for(int trial=-4;trial<repeats;++trial)for(int order=0;order<3;++order){
    int schedule=(order+trial+6)%3,seed=(trial+4)%2+1;
    HIP(hipMemsetAsync(q,0xff,heads*D*sizeof(float),streams[0]));HIP(hipMemsetAsync(sums,0xff,4*heads*sizeof(Summary),streams[0]));HIP(hipMemsetAsync(spans,0,times.size()*sizeof(Span),streams[0]));HIP(hipStreamSynchronize(streams[0]));
    auto host_start=std::chrono::steady_clock::now();HIP(hipEventRecord(start,streams[0]));prepare<<<(heads*D+255)/256,256,0,streams[0]>>>(q,heads,seed);
    for(int st=0;st<stages;++st){
     if(schedule==0){for(int b=0;b<branches;++b)attention_part<false><<<heads,THREADS,0,streams[0]>>>(q,k,v,sums,spans,heads,total,branches,st,stage_tokens,bounds,b);}
     else if(schedule==2)attention_part<true><<<heads*branches,THREADS,0,streams[0]>>>(q,k,v,sums,spans,heads,total,branches,st,stage_tokens,bounds,0);
     else{
      HIP(hipEventRecord(ready,streams[0]));
      for(int b=1;b<branches;++b){HIP(hipStreamWaitEvent(streams[b],ready,0));attention_part<false><<<heads,THREADS,0,streams[b]>>>(q,k,v,sums,spans,heads,total,branches,st,stage_tokens,bounds,b);HIP(hipEventRecord(done[b],streams[b]));}
      attention_part<false><<<heads,THREADS,0,streams[0]>>>(q,k,v,sums,spans,heads,total,branches,st,stage_tokens,bounds,0);
      for(int b=1;b<branches;++b)HIP(hipStreamWaitEvent(streams[0],done[b],0));
     }
     join_update<<<heads,D,0,streams[0]>>>(sums,q,spans,heads,branches,st);
    }
    HIP(hipGetLastError());HIP(hipEventRecord(stop,streams[0]));HIP(hipEventSynchronize(stop));auto host_stop=std::chrono::steady_clock::now();float elapsed;HIP(hipEventElapsedTime(&elapsed,start,stop));
    HIP(hipMemcpy(actual.data(),q,actual.size()*sizeof(float),hipMemcpyDeviceToHost));HIP(hipMemcpy(times.data(),spans,times.size()*sizeof(Span),hipMemcpyDeviceToHost));
    double error=0;for(size_t i=0;i<actual.size();++i){if(!std::isfinite(actual[i]))return 4;error=std::max(error,std::abs(double(actual[i])-refs[seed-1][i]));}
    if(error>5e-5){fprintf(stderr,"reference failure config=%s B=%d schedule=%s seed=%d error=%.9g\n",cfg.name,branches,names[schedule],seed,error);return 4;}
    double scale=1000.0/rate,span_sum=0,union_sum=0,join_gaps=0,join_spans=0,skews=0,continuation=0;
    unsigned long long previous_join_end=0;
    for(int st=0;st<stages;++st){
     unsigned long long first=~0ULL,last=0,last_begin=0,join_lo=~0ULL,join_hi=0,serial_end=0;
     for(int b=0;b<=branches;++b){unsigned long long lo=~0ULL,hi=0;
      for(int h=0;h<heads;++h){auto t=times[(st*(branches+1)+b)*heads+h];if(!t.begin||t.end<=t.begin)return 5;lo=std::min(lo,t.begin);hi=std::max(hi,t.end);}
      if(trial==0)fprintf(stderr,"TIMELINE config=%s branches=%d schedule=%s stage=%d part=%d begin=%llu end=%llu\n",cfg.name,branches,names[schedule],st,b,lo,hi);
      if(b<branches){if(st>0&&lo+100<previous_join_end)return 5;if(schedule==0&&b>0&&lo+100<serial_end)return 5;serial_end=hi;first=std::min(first,lo);last=std::max(last,hi);last_begin=std::max(last_begin,lo);span_sum+=(hi-lo)*scale;}
      else{join_lo=lo;join_hi=hi;}
     }
     if(join_lo+100<last)return 5;
     union_sum+=(last-first)*scale;join_gaps+=(double(join_lo)-double(last))*scale;join_spans+=(join_hi-join_lo)*scale;skews+=(last_begin-first)*scale;
     if(st>0)continuation+=(double(first)-double(previous_join_end))*scale;previous_join_end=join_hi;
    }
    if(trial>=0)printf("%s,%d,%d,%d,%d,%d,%d,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.9g,1\n",cfg.name,heads,total,stages,branches,trial,seed,names[schedule],elapsed*1000,std::chrono::duration<double,std::micro>(host_stop-host_start).count(),span_sum,union_sum,span_sum-union_sum,join_gaps,join_spans,skews,continuation,error);
   }
  }
  for(int b=0;b<4;++b)HIP(hipStreamSynchronize(streams[b]));HIP(hipFree(q));HIP(hipFree(k));HIP(hipFree(v));HIP(hipFree(sums));HIP(hipFree(spans));
 }
 for(int b=0;b<4;++b){HIP(hipEventDestroy(done[b]));HIP(hipStreamDestroy(streams[b]));}HIP(hipEventDestroy(ready));HIP(hipEventDestroy(start));HIP(hipEventDestroy(stop));
}
