#include <hip/hip_runtime.h>
#include <cstdint>
#include <cstdio>
#define H(x) do {auto e=(x); if(e!=hipSuccess){std::fprintf(stderr,"%d %s: %s\n",__LINE__,#x,hipGetErrorString(e));return int(e);}}while(0)
struct State {hipStream_t main,side;hipEvent_t ready_event,done_event;void* ready;void* done;uint32_t generation=0;};
extern "C" int setup(void** output,void* main,void* side){
 auto* s=new State{};s->main=(hipStream_t)main;s->side=(hipStream_t)side;
 H(hipEventCreateWithFlags(&s->ready_event,hipEventDisableTiming));H(hipEventCreateWithFlags(&s->done_event,hipEventDisableTiming));
 H(hipExtMallocWithFlags(&s->ready,8,hipMallocSignalMemory));H(hipExtMallocWithFlags(&s->done,8,hipMallocSignalMemory));
 H(hipStreamWriteValue32(s->main,s->ready,0,0));H(hipStreamWriteValue32(s->main,s->done,0,0));H(hipStreamSynchronize(s->main));*output=s;return 0;
}
// 0 combined graph; 1 separate graphs/serial; 2 separate graphs/events;
// 3 separate graphs/stream-memory (GPU polling or CP, selected before HIP init).
extern "C" int launch(void* state,void* graph,void* q,void* k,int mode,int launches){
 auto& s=*(State*)state;
 for(int i=0;i<launches;++i){
  if(mode==0){H(hipGraphLaunch((hipGraphExec_t)graph,s.main));continue;}
  if(mode==1){H(hipGraphLaunch((hipGraphExec_t)q,s.main));H(hipGraphLaunch((hipGraphExec_t)k,s.main));continue;}
  uint32_t generation=++s.generation;if(generation>=0x7fffffffu)return int(hipErrorInvalidValue);
  // Same fork/join happens every pair. Monotonic generations prohibit stale success.
  if(mode==2){H(hipEventRecord(s.ready_event,s.main));}
  else{H(hipStreamWriteValue32(s.main,s.ready,generation,0));}
  H(hipGraphLaunch((hipGraphExec_t)q,s.main));
  if(mode==2){H(hipStreamWaitEvent(s.side,s.ready_event,0));}
  else{H(hipStreamWaitValue32(s.side,s.ready,generation,hipStreamWaitValueGte,0xffffffffu));}
  H(hipGraphLaunch((hipGraphExec_t)k,s.side));
  if(mode==2){H(hipEventRecord(s.done_event,s.side));H(hipStreamWaitEvent(s.main,s.done_event,0));}
  else{H(hipStreamWriteValue32(s.side,s.done,generation,0));H(hipStreamWaitValue32(s.main,s.done,generation,hipStreamWaitValueGte,0xffffffffu));}
 }
 return 0;
}
extern "C" int inspect(void* state,uint32_t* result){
 auto& s=*(State*)state;H(hipStreamSynchronize(s.main));H(hipStreamSynchronize(s.side));
 uint32_t values[2]{};H(hipMemcpy(values,s.ready,4,hipMemcpyDeviceToHost));H(hipMemcpy(values+1,s.done,4,hipMemcpyDeviceToHost));
 result[0]=s.generation;result[1]=values[0];result[2]=values[1];return 0;
}
extern "C" int cleanup(void* state){auto* s=(State*)state;H(hipStreamSynchronize(s->main));H(hipStreamSynchronize(s->side));H(hipEventDestroy(s->ready_event));H(hipEventDestroy(s->done_event));H(hipFree(s->ready));H(hipFree(s->done));delete s;return 0;}
