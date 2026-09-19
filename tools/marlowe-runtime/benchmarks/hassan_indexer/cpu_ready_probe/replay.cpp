#include <hsa/hsa.h>
#include <hsa/hsa_ext_amd.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <memory>
#include <limits>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>
#define H(call) do { auto e=(call); if(e!=HSA_STATUS_SUCCESS) { const char* t=nullptr; hsa_status_string(e,&t); throw std::runtime_error(std::string(#call)+": "+(t?t:"unknown")); } } while(0)
static void require(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
hsa_agent_t gpu{},cpu{};
hsa_amd_memory_pool_t pool{};
unsigned gpu_count=0;
std::atomic<int> queue_error{0};
hsa_status_t agents(hsa_agent_t a,void*) {
  hsa_device_type_t t; H(hsa_agent_get_info(a,HSA_AGENT_INFO_DEVICE,&t));
  if(t==HSA_DEVICE_TYPE_GPU) { gpu=a; ++gpu_count; }
  if(t==HSA_DEVICE_TYPE_CPU && !cpu.handle) cpu=a;
  return HSA_STATUS_SUCCESS;
}
hsa_status_t pools(hsa_amd_memory_pool_t p,void*) {
  hsa_amd_segment_t seg; H(hsa_amd_memory_pool_get_info(p,HSA_AMD_MEMORY_POOL_INFO_SEGMENT,&seg));
  if(seg!=HSA_AMD_SEGMENT_GLOBAL) return HSA_STATUS_SUCCESS;
  uint32_t flags; bool allowed;
  H(hsa_amd_memory_pool_get_info(p,HSA_AMD_MEMORY_POOL_INFO_GLOBAL_FLAGS,&flags));
  H(hsa_amd_memory_pool_get_info(p,HSA_AMD_MEMORY_POOL_INFO_RUNTIME_ALLOC_ALLOWED,&allowed));
  if(allowed && (flags&HSA_AMD_MEMORY_POOL_GLOBAL_FLAG_FINE_GRAINED) &&
      (flags&HSA_AMD_MEMORY_POOL_GLOBAL_FLAG_KERNARG_INIT)) pool=p;
  return HSA_STATUS_SUCCESS;
}
struct Memory {
  void* p=nullptr;
  explicit Memory(size_t n,uint32_t flags=0) {
    H(hsa_amd_memory_pool_allocate(pool,n,flags,&p));
    H(hsa_amd_agents_allow_access(1,&gpu,nullptr,p));
    std::memset(p,0,n);
  }
  ~Memory() { if(p) hsa_amd_memory_pool_free(p); }
};
[[noreturn]] void fail_inflight(const char* message) {
  std::fprintf(stderr,"INFLIGHT_FAILURE %s; exiting without reclaiming live GPU storage\n",message);
  std::fflush(stderr); std::_Exit(2);
}
struct Signal {
  hsa_signal_t s{};
  Signal() { H(hsa_amd_signal_create(1,0,nullptr,HSA_AMD_SIGNAL_IPC,&s)); }
  ~Signal() { if(s.handle) hsa_signal_destroy(s); }
  void reset() { hsa_signal_store_relaxed(s,1); }
  long long* pointer() {
    volatile hsa_signal_value_t* p=nullptr;
    H(hsa_amd_signal_value_pointer(s,&p));
    return reinterpret_cast<long long*>(const_cast<hsa_signal_value_t*>(p));
  }
  void wait() {
    auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(15);
    unsigned polls=0;
    while(hsa_signal_load_scacquire(s)!=0) {
      if((!(polls++&1023)) && (queue_error.load() || std::chrono::steady_clock::now()>deadline))
        fail_inflight("completion timeout or queue error");
      __builtin_ia32_pause();
    }
    if(queue_error.load()) fail_inflight("queue error after completion");
  }
};
struct alignas(64) Packet { unsigned char bytes[64]{}; };
static_assert(sizeof(Packet)==64);
constexpr uint16_t header(unsigned type,bool ordered,bool system) {
  return (type<<HSA_PACKET_HEADER_TYPE) | (unsigned(ordered)<<HSA_PACKET_HEADER_BARRIER) |
    ((system?HSA_FENCE_SCOPE_SYSTEM:HSA_FENCE_SCOPE_NONE)<<HSA_PACKET_HEADER_SCACQUIRE_FENCE_SCOPE) |
    ((system?HSA_FENCE_SCOPE_SYSTEM:HSA_FENCE_SCOPE_NONE)<<HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE);
}
Packet barrier(hsa_signal_t done={},bool system=false) {
  hsa_barrier_and_packet_t b{};
  b.header=header(HSA_PACKET_TYPE_BARRIER_AND,true,system); b.completion_signal=done;
  Packet out; std::memcpy(out.bytes,&b,64); return out;
}
Packet boundary(bool entry,hsa_signal_t done={},hsa_signal_t gate={}) {
  hsa_barrier_and_packet_t b{};
  b.header=(HSA_PACKET_TYPE_BARRIER_AND<<HSA_PACKET_HEADER_TYPE) |
      (1<<HSA_PACKET_HEADER_BARRIER) |
      ((entry?HSA_FENCE_SCOPE_SYSTEM:HSA_FENCE_SCOPE_NONE)<<HSA_PACKET_HEADER_SCACQUIRE_FENCE_SCOPE) |
      ((entry?HSA_FENCE_SCOPE_NONE:HSA_FENCE_SCOPE_SYSTEM)<<HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE);
  b.completion_signal=done;
  if(entry) b.dep_signal[0]=gate;
  Packet out; std::memcpy(out.bytes,&b,64); return out;
}
struct Publication { uint64_t first,last,read_before; bool wrapped; };
struct Queue {
  hsa_queue_t* q=nullptr;
  Queue() { H(hsa_queue_create(gpu,4096,HSA_QUEUE_TYPE_SINGLE,
      [](hsa_status_t e,hsa_queue_t*,void*) { queue_error.store(int(e)); },
      nullptr,UINT32_MAX,UINT32_MAX,&q)); }
  ~Queue() { if(q) hsa_queue_destroy(q); }
  bool fits(size_t count) const {
    uint64_t w=hsa_queue_load_write_index_relaxed(q),r=hsa_queue_load_read_index_scacquire(q);
    return count && count<=q->size && w-r<=q->size-count;
  }
  Publication publish(const std::vector<Packet>& packets) {
    require(fits(packets.size()),"prepublication capacity rejection");
    uint64_t w=hsa_queue_load_write_index_relaxed(q),r=hsa_queue_load_read_index_scacquire(q);
    // No concurrent CPU producer. Every slot is validated before reservation.
    for(size_t i=0;i<packets.size();++i) {
      auto* slot=reinterpret_cast<uint16_t*>(static_cast<char*>(q->base_address)+64*((w+i)&(q->size-1)));
      require((__atomic_load_n(slot,__ATOMIC_ACQUIRE)&0xff)==HSA_PACKET_TYPE_INVALID,
          "slot was not invalid before reservation");
    }
    uint64_t first=hsa_queue_add_write_index_relaxed(q,packets.size());
    if(first!=w) fail_inflight("unexpected concurrent writer");
    // All storage and receipts already exist. No fallible operation after reservation.
    for(size_t i=0;i<packets.size();++i) {
      auto* dst=static_cast<char*>(q->base_address)+64*((first+i)&(q->size-1));
      std::memcpy(dst+4,packets[i].bytes+4,60);
      if(i) { uint32_t word; std::memcpy(&word,packets[i].bytes,4);
        __atomic_store_n(reinterpret_cast<uint32_t*>(dst),word,__ATOMIC_RELAXED); }
    }
    auto* head=static_cast<char*>(q->base_address)+64*(first&(q->size-1));
    uint32_t word; std::memcpy(&word,packets[0].bytes,4);
    __atomic_store_n(reinterpret_cast<uint32_t*>(head),word,__ATOMIC_RELEASE);
    hsa_signal_store_screlease(q->doorbell_signal,first+packets.size()-1);
    return {first,first+packets.size()-1,r,
      (first&(q->size-1))+packets.size()>q->size};
  }
};
Packet dependent(hsa_signal_t signal) {
  auto out=barrier();
  reinterpret_cast<hsa_barrier_and_packet_t*>(out.bytes)->dep_signal[0]=signal;
  return out; // Exact K dispatchBlockingWait: ordered AND, NONE/NONE scopes.
}
uint64_t raw_ns() {
  timespec t{};
  if(clock_gettime(CLOCK_MONOTONIC_RAW,&t)!=0) fail_inflight("clock_gettime failed");
  return uint64_t(t.tv_sec)*1000000000+uint64_t(t.tv_nsec);
}
struct Metrics {
  double prepare_us,publish_us,gate_hold_us,latency_us,dispatch_envelope_us;
  uint64_t system_hz,first0,last0,first1,last1,queue0,queue1,completed_signals;
};
struct LayerReceipt {
  uint64_t layer,first_lane,observed_ns,first_action_ns,both_actions_ns;
  uint64_t before0q,before0k,before1q,before1k;
  uint64_t first0,last0,read0,first1,last1,read1;
};
static_assert(sizeof(LayerReceipt)==120);
struct Replay {
  unsigned group,units;
  Queue queues[2];
  Signal gate,done[2];
  std::vector<std::unique_ptr<Signal>> kernels;
  std::vector<Packet> packets[2];
  std::vector<std::vector<Packet>> chunks[2];
  std::vector<Packet> originals;
  bool inflight=false;
  uint64_t system_hz=0;
  Replay(const void* templates,unsigned group_,unsigned units_):group(group_),units(units_) {
    require(group && units && units%group==0 && units<=512,"bounded complete graph repetitions required");
    H(hsa_system_get_info(HSA_SYSTEM_INFO_TIMESTAMP_FREQUENCY,&system_hz));
    originals.resize(2*group); std::memcpy(originals.data(),templates,2*group*64);
    for(unsigned i=0;i<2*group;++i) {
      const auto& p=*reinterpret_cast<const hsa_kernel_dispatch_packet_t*>(originals[i].bytes);
      require((p.header&255)==HSA_PACKET_TYPE_KERNEL_DISPATCH && ((p.header>>8)&1),"not ordered kernel dispatch");
      require(((p.header>>9)&3)==1 && ((p.header>>11)&3)==1,"expected original AGENT/AGENT scopes");
      require(p.private_segment_size==0 && p.group_segment_size==61440 && p.kernel_object && p.kernarg_address,"unexpected resources");
      require(p.reserved0==0 && p.reserved2==0,"unexpected reserved packet state");
    }
    kernels.reserve(2*units);
    for(unsigned i=0;i<2*units;++i) kernels.emplace_back(std::make_unique<Signal>());
    for(unsigned lane=0;lane<2;++lane) {
      auto& all=packets[lane]; all.reserve(2*units+1); chunks[lane].resize(units);
      for(unsigned i=0;i<units;++i) {
        auto& part=chunks[lane][i]; part.reserve(3);
        if(!i) part.push_back(boundary(true,{},gate.s));
        else part.push_back(dependent(kernels[2*(i-1)+(1-lane)]->s));
        Packet packet=originals[2*(i%group)+lane];
        reinterpret_cast<hsa_kernel_dispatch_packet_t*>(packet.bytes)->completion_signal=kernels[2*i+lane]->s;
        part.push_back(packet);
        if(i+1==units) part.push_back(boundary(false,done[lane].s));
        all.insert(all.end(),part.begin(),part.end());
      }
      require(all.size()==2*units+1 && all.size()<=queues[lane].q->size,"graph exceeds queue capability");
    }
  }
  ~Replay() { if(inflight) fail_inflight("attempt to destroy live replay"); }
  void run(unsigned mode,bool profile,unsigned first_lane,Metrics& metric,uint64_t* times,LayerReceipt* layers) {
    require(mode<3 && first_lane<2 && !inflight,"invalid replay mode/state");
    for(auto& q:queues) H(hsa_amd_profiling_set_profiler_enabled(q.q,profile));
    std::memset(layers,0,(units-1)*sizeof(LayerReceipt));
    uint64_t start=raw_ns();
    gate.reset(); for(auto& s:done) s.reset(); for(auto& s:kernels) s->reset();
    for(unsigned lane=0;lane<2;++lane) require(queues[lane].fits(packets[lane].size()),"queue capacity before publication");
    Publication receipts[2]{};
    uint64_t prepared=raw_ns(); inflight=true;
    try {
      for(unsigned n=0;n<2;++n) {
        unsigned lane=n?1-first_lane:first_lane;
        receipts[lane]=queues[lane].publish(mode==2?chunks[lane][0]:packets[lane]);
      }
    } catch (...) { fail_inflight("initial publication failed in live-work phase"); }
    uint64_t published=raw_ns();
    std::this_thread::sleep_for(std::chrono::microseconds(200));
    uint64_t released=raw_ns(); hsa_signal_store_screlease(gate.s,0);
    // All allocations and packet construction happened before publication.
    // Both observing modes execute matching signal checks/timestamp records.
    // Mode2 additionally supplies packets only after actual predecessor completion.
    if(mode) {
      try {
        for(unsigned i=1;i<units;++i) {
          kernels[2*(i-1)]->wait(); kernels[2*(i-1)+1]->wait();
          auto& row=layers[i-1]; row.layer=i; row.first_lane=(first_lane+i)%2;
          row.observed_ns=raw_ns();
          for(unsigned n=0;n<2;++n) {
            unsigned lane=n?1-row.first_lane:row.first_lane;
            uint64_t q=hsa_signal_load_scacquire(kernels[2*(i-1)]->s);
            uint64_t k=hsa_signal_load_scacquire(kernels[2*(i-1)+1]->s);
            require(q==0 && k==0,"both predecessors must really be complete before each publication");
            if(lane==0) { row.before0q=q;row.before0k=k; }
            else { row.before1q=q;row.before1k=k; }
            if(mode==2) {
              auto pub=queues[lane].publish(chunks[lane][i]);
              require(pub.first==receipts[lane].last+1,"noncontiguous layer publication");
              receipts[lane].last=pub.last;
              if(lane==0) { row.first0=pub.first;row.last0=pub.last;row.read0=pub.read_before; }
              else { row.first1=pub.first;row.last1=pub.last;row.read1=pub.read_before; }
            }
            uint64_t end=raw_ns();
            if(!n) row.first_action_ns=end; else row.both_actions_ns=end;
          }
        }
      } catch (...) { fail_inflight("layer observation/publication failed with live GPU storage"); }
    }
    done[0].wait(); done[1].wait();
    uint64_t end=raw_ns(); inflight=false;
    for(auto& s:kernels) require(hsa_signal_load_scacquire(s->s)==0,"not every unique dispatch completed");
    uint64_t earliest=std::numeric_limits<uint64_t>::max(),latest=0;
    if(profile) {
      for(unsigned i=0;i<2*units;++i) {
        hsa_amd_profiling_dispatch_time_t t{};
        H(hsa_amd_profiling_get_dispatch_time(gpu,kernels[i]->s,&t));
        require(t.start && t.end>=t.start,"invalid HSA dispatch timestamps");
        times[2*i]=t.start; times[2*i+1]=t.end;
        earliest=std::min(earliest,t.start); latest=std::max(latest,t.end);
      }
    }
    metric={double(prepared-start)/1000,double(published-prepared)/1000,double(released-published)/1000,
      double(end-released)/1000,profile?double(latest-earliest)*1e6/system_hz:0.0,system_hz,
      receipts[0].first,receipts[0].last,receipts[1].first,receipts[1].last,
      queues[0].q->id,queues[1].q->id,2*units};
  }
};
extern "C" int replay_create(const void* packets,unsigned group,unsigned units,void** result) {
  try {
    H(hsa_init());
    gpu={};cpu={};pool={};gpu_count=0;queue_error.store(0);
    H(hsa_iterate_agents(agents,nullptr)); require(gpu_count==1 && cpu.handle,"require one visible GPU");
    char name[64]{}; H(hsa_agent_get_info(gpu,HSA_AGENT_INFO_NAME,name)); require(std::string(name)=="gfx950","gfx950 required");
    H(hsa_amd_agent_iterate_memory_pools(cpu,pools,nullptr)); require(pool.handle,"no fine-grained kernarg pool");
    *result=new Replay(packets,group,units); return 0;
  } catch(const std::exception& e) { std::fprintf(stderr,"CREATE_ERROR %s\n",e.what()); return 1; }
}
extern "C" int replay_run(void* state,unsigned mode,unsigned profile,unsigned first_lane,Metrics* metric,uint64_t* times,LayerReceipt* layers) {
  try { static_cast<Replay*>(state)->run(mode,profile,first_lane,*metric,times,layers); return 0; }
  catch(const std::exception& e) { std::fprintf(stderr,"REPLAY_ERROR %s\n",e.what()); return 1; }
}
extern "C" int replay_dump(void* state,const char* directory) {
  try {
    auto& r=*static_cast<Replay*>(state); require(!r.inflight,"cannot dump live replay");
    std::string dir=directory;
    for(unsigned mode=0;mode<3;++mode) for(unsigned lane=0;lane<2;++lane) {
      std::ofstream f(dir+"/packets-m"+std::to_string(mode)+"-q"+std::to_string(lane)+".bin",std::ios::binary);
      const auto& p=r.packets[lane]; f.write(reinterpret_cast<const char*>(p.data()),p.size()*64); require(bool(f),"packet dump failed");
    }
    std::ofstream signals(dir+"/signals.csv"); signals<<"index,handle,pointer\n";
    for(unsigned i=0;i<r.kernels.size();++i) signals<<i<<','<<r.kernels[i]->s.handle<<','<<reinterpret_cast<uintptr_t>(r.kernels[i]->pointer())<<'\n';
    return 0;
  } catch(const std::exception& e) { std::fprintf(stderr,"DUMP_ERROR %s\n",e.what()); return 1; }
}
extern "C" int replay_destroy(void* state) {
  delete static_cast<Replay*>(state); return hsa_shut_down()==HSA_STATUS_SUCCESS?0:1;
}
