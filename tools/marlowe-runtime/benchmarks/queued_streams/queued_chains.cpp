// Reuse the attention math and independent CPU oracle from the original micro.
#define STREAM_CHAINS_KERNELS_ONLY
#include "../attention_stream_chains/stream_chains.cpp"

struct TrialStorage {
  float* q; Summary* sums; Span* spans; hipEvent_t begin, end;
};
int main(int argc, char** argv) {
  if (argc != 3 || !getenv("SLURM_JOB_ID")) return 2;
  const int repeats = std::stoi(argv[1]), heads = 128, total = 16384, stages = 64;
  if (repeats < 3) return 2;
  int count, rate; HIP(hipGetDeviceCount(&count)); if (count != 1) return 2;
  HIP(hipDeviceGetAttribute(&rate, hipDeviceAttributeWallClockRate, 0));
  std::ifstream maps("/proc/self/maps");
  for (std::string s; std::getline(maps,s);) if (s.find("libamdhip64") != std::string::npos || s.find("libhsa-runtime64") != std::string::npos) fprintf(stderr,"LIBRARY %s\n",s.c_str());
  hipStream_t streams[4]; hipEvent_t ready, done[4];
  for (int b=0;b<4;++b) { HIP(hipStreamCreateWithFlags(&streams[b],hipStreamNonBlocking)); HIP(hipEventCreateWithFlags(&done[b],hipEventDisableTiming)); }
  HIP(hipEventCreateWithFlags(&ready,hipEventDisableTiming));
  float *k,*v; size_t n=size_t(heads)*total*D;
  HIP(hipMalloc(&k,n*sizeof(float))); HIP(hipMalloc(&v,n*sizeof(float)));
  initialize<<<(n+255)/256,256,0,streams[0]>>>(k,v,n); HIP(hipGetLastError()); HIP(hipStreamSynchronize(streams[0]));
  std::vector<std::vector<float>> refs;
  for(int seed=1;seed<=2;++seed) refs.push_back(cached_reference(heads,total,stages,seed,argv[2]));
  std::vector<TrialStorage> storage(16);
  for(auto& t:storage) {
    HIP(hipMalloc(&t.q,heads*D*sizeof(float))); HIP(hipMalloc(&t.sums,4*heads*sizeof(Summary)));
    HIP(hipMalloc(&t.spans,stages*5*heads*sizeof(Span))); HIP(hipEventCreate(&t.begin)); HIP(hipEventCreate(&t.end));
  }
  puts("config,branches,depth,batch,trial,total_us,host_per_trial_us,branch_span_sum_us,branch_envelope_sum_us,join_gap_sum_us,branch_start_skew_sum_us,max_abs_error,correct");
  for(bool skew:{false,true}) for(int branches:{2,4}) for(int depth:{1,16}) {
    Bounds bounds{}; bounds.offset[branches]=total/stages;
    if(skew) { bounds.offset[1]=(total/stages)*7/8; for(int b=2;b<branches;++b) bounds.offset[b]=bounds.offset[1]+((total/stages)-bounds.offset[1])*(b-1)/(branches-1); }
    else for(int b=1;b<branches;++b) bounds.offset[b]=(total/stages)*b/branches;
    for(int batch=-1;batch<repeats;++batch) {
      for(int trial=0;trial<depth;++trial) {
        auto& t=storage[trial]; HIP(hipMemsetAsync(t.q,0xff,heads*D*sizeof(float),streams[0]));
        HIP(hipMemsetAsync(t.sums,0xff,4*heads*sizeof(Summary),streams[0])); HIP(hipMemsetAsync(t.spans,0,stages*5*heads*sizeof(Span),streams[0]));
      }
      HIP(hipStreamSynchronize(streams[0]));
      auto host_begin=std::chrono::steady_clock::now();
      // No host sync/query/readback between trials. Each has independent outputs
      // and timing storage. Stream 0 joins every branch before the next trial.
      for(int trial=0;trial<depth;++trial) {
        auto& t=storage[trial]; int seed=trial%2+1;
        HIP(hipEventRecord(t.begin,streams[0])); prepare<<<(heads*D+255)/256,256,0,streams[0]>>>(t.q,heads,seed);
        for(int st=0;st<stages;++st) {
          HIP(hipEventRecord(ready,streams[0]));
          for(int b=1;b<branches;++b) {
            HIP(hipStreamWaitEvent(streams[b],ready,0));
            attention_part<false><<<heads,THREADS,0,streams[b]>>>(t.q,k,v,t.sums,t.spans,heads,total,branches,st,total/stages,bounds,b);
            HIP(hipEventRecord(done[b],streams[b]));
          }
          attention_part<false><<<heads,THREADS,0,streams[0]>>>(t.q,k,v,t.sums,t.spans,heads,total,branches,st,total/stages,bounds,0);
          for(int b=1;b<branches;++b) HIP(hipStreamWaitEvent(streams[0],done[b],0));
          join_update<<<heads,D,0,streams[0]>>>(t.sums,t.q,t.spans,heads,branches,st);
        }
        HIP(hipGetLastError()); HIP(hipEventRecord(t.end,streams[0]));
      }
      HIP(hipEventSynchronize(storage[depth-1].end));
      double host=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-host_begin).count()/depth;
      for(int trial=0;trial<depth;++trial) {
        auto& t=storage[trial]; float elapsed; HIP(hipEventElapsedTime(&elapsed,t.begin,t.end));
        std::vector<float> actual(heads*D); std::vector<Span> times(stages*(branches+1)*heads);
        HIP(hipMemcpy(actual.data(),t.q,actual.size()*sizeof(float),hipMemcpyDeviceToHost)); HIP(hipMemcpy(times.data(),t.spans,times.size()*sizeof(Span),hipMemcpyDeviceToHost));
        double error=0,span=0,envelope=0,gaps=0,skews=0,scale=1000.0/rate;
        for(size_t i=0;i<actual.size();++i) { if(!std::isfinite(actual[i])) return 4; error=std::max(error,std::abs(double(actual[i])-refs[trial%2][i])); }
        if(error>5e-5) return 4;
        unsigned long long previous_end=0;
        for(int st=0;st<stages;++st) {
          unsigned long long first=~0ULL,last=0,last_start=0,join_begin=~0ULL,join_end=0;
          for(int b=0;b<=branches;++b) {
            unsigned long long lo=~0ULL,hi=0;
            for(int h=0;h<heads;++h) { auto x=times[(st*(branches+1)+b)*heads+h]; if(!x.begin||x.end<=x.begin) return 5; lo=std::min(lo,x.begin); hi=std::max(hi,x.end); }
            if(b<branches) { if(st&&lo+100<previous_end) return 5; first=std::min(first,lo); last=std::max(last,hi); last_start=std::max(last_start,lo); span+=(hi-lo)*scale; }
            else { join_begin=lo; join_end=hi; }
          }
          if(join_begin+100<last) return 5;
          envelope+=(last-first)*scale; gaps+=(double(join_begin)-last)*scale; skews+=(last_start-first)*scale; previous_end=join_end;
        }
        if(batch>=0) printf("%s,%d,%d,%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.9g,1\n",skew?"uneven-64":"balanced-64",branches,depth,batch,trial,elapsed*1000,host,span,envelope,gaps,skews,error);
      }
    }
  }
  for(auto& t:storage) { HIP(hipFree(t.q)); HIP(hipFree(t.sums)); HIP(hipFree(t.spans)); HIP(hipEventDestroy(t.begin)); HIP(hipEventDestroy(t.end)); }
  for(int b=0;b<4;++b) { HIP(hipStreamDestroy(streams[b])); HIP(hipEventDestroy(done[b])); }
  HIP(hipEventDestroy(ready)); HIP(hipFree(k)); HIP(hipFree(v));
}
