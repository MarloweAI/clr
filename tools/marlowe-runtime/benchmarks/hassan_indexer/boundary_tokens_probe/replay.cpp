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
#include <emmintrin.h>
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
  unsigned placement;
  hsa_amd_pointer_info_t info{};
  hsa_device_type_t owner_type{};
  explicit Signal(unsigned where=99):placement(where) {
    if(where==99) H(hsa_amd_signal_create(1,0,nullptr,HSA_AMD_SIGNAL_IPC,&s));
    else {
      require(where<3,"unknown placement");
      uint64_t flags=HSA_AMD_SIGNAL_AMD_GPU_ONLY;
      if(where) flags|=uint64_t(1)<<63;
      if(where==2) flags|=uint64_t(1)<<62;
      H(hsa_amd_signal_create(1,1,&gpu,flags,&s));
      info.size=sizeof(info);
      uint32_t count=0;hsa_agent_t* access=nullptr;
      H(hsa_amd_pointer_info(reinterpret_cast<void*>(s.handle),&info,std::malloc,&count,&access));
      bool accessible=false;for(unsigned i=0;i<count;++i) accessible|=access[i].handle==gpu.handle;
      std::free(access);
      require(accessible && info.type==HSA_EXT_POINTER_TYPE_HSA,"signal allocation/access type");
      require(info.hostBaseAddress && info.hostBaseAddress==info.agentBaseAddress,"signal CPU/GPU mapping differs");
      require(info.global_flags&HSA_AMD_MEMORY_POOL_GLOBAL_FLAG_FINE_GRAINED,"signal is not fine-grained");
      H(hsa_agent_get_info(info.agentOwner,HSA_AGENT_INFO_DEVICE,&owner_type));
      require(owner_type==(where==2?HSA_DEVICE_TYPE_GPU:HSA_DEVICE_TYPE_CPU),"wrong signal physical owner");
      if(where==2) require(info.agentOwner.handle==gpu.handle,"wrong local GPU owner");
      require(!(s.handle&63) && (s.handle&4095)<=4096-128,"invalid ABI alignment/page containment");
      if(where) require(s.handle==reinterpret_cast<uintptr_t>(info.agentBaseAddress) && info.sizeInBytes>=4096 && !(s.handle&4095),"diagnostic storage not dedicated page");
      guards();
    }
  }
  ~Signal() { if(s.handle && hsa_signal_destroy(s)!=HSA_STATUS_SUCCESS) std::abort(); }
  void reset() { hsa_signal_store_relaxed(s,1); }
  long long* pointer() {
    volatile hsa_signal_value_t* p=nullptr; H(hsa_amd_signal_value_pointer(s,&p));
    return reinterpret_cast<long long*>(const_cast<hsa_signal_value_t*>(p));
  }
  void guards() const {
    if(placement==1 || placement==2) {
      auto* p=reinterpret_cast<volatile const uint64_t*>(s.handle);
      require(p[128/8]==0x71a9b02cc38e5d64ULL && p[4088/8]==0x71a9b02cc38e5d64ULL,"signal guard overwritten");
    }
  }
  void wait() {
    require(placement==99,"CPU waits forbidden on internal GPU-only signals");
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
  double prepare_us,publish_us,total_us,latency_us,dispatch_envelope_us;
  uint64_t system_hz,first0,last0,first1,last1,queue0,queue1,completed_signals;
};
struct Replay {
  unsigned group,units,graphs;
  Queue queues[2];
  std::vector<std::unique_ptr<Signal>> tokens[3];
  std::vector<std::unique_ptr<Signal>> finals;
  std::vector<Packet> packets[3][2],originals;
  bool inflight=false;
  uint64_t system_hz=0;
  Replay(const void* templates,unsigned group_,unsigned units_):group(group_),units(units_),graphs(units_/group_) {
    require((group==1 || group==50) && units && units%group==0 && units<=512,"bounded whole graphs required");
    H(hsa_system_get_info(HSA_SYSTEM_INFO_TIMESTAMP_FREQUENCY,&system_hz));
    originals.resize(2*group);std::memcpy(originals.data(),templates,2*group*64);
    for(const auto& raw:originals) {
      const auto& p=*reinterpret_cast<const hsa_kernel_dispatch_packet_t*>(raw.bytes);
      require((p.header&255)==HSA_PACKET_TYPE_KERNEL_DISPATCH && ((p.header>>8)&1),"ordered original dispatch required");
      require(((p.header>>9)&3)==1 && ((p.header>>11)&3)==1,"original AGENT scopes required");
      require(!p.private_segment_size && p.group_segment_size==61440 && p.kernel_object && p.kernarg_address,"original resources required");
      require(!p.reserved0 && !p.reserved2,"unexpected reserved fields");
    }
    for(unsigned i=0;i<graphs;++i) finals.emplace_back(std::make_unique<Signal>());
    for(unsigned mode=0;mode<3;++mode) {
      for(unsigned i=0;i<2*units+graphs;++i) tokens[mode].emplace_back(std::make_unique<Signal>(mode));
      for(unsigned graph=0;graph<graphs;++graph) {
        const hsa_signal_t entry=tokens[mode][2*units+graph]->s;
        // Queue0 orders this graph after the previous graph's final join.
        packets[mode][0].push_back(barrier(entry,true));
        auto wait=boundary(true,{},entry);
        packets[mode][1].push_back(wait);
        for(unsigned pair=0;pair<group;++pair) for(unsigned lane=0;lane<2;++lane) {
          const unsigned i=graph*group+pair;
          if(pair) packets[mode][lane].push_back(dependent(tokens[mode][2*(i-1)+(1-lane)]->s));
          Packet raw=originals[2*pair+lane];
          reinterpret_cast<hsa_kernel_dispatch_packet_t*>(raw.bytes)->completion_signal=tokens[mode][2*i+lane]->s;
          packets[mode][lane].push_back(raw);
        }
        auto join=barrier(finals[graph]->s,true);
        reinterpret_cast<hsa_barrier_and_packet_t*>(join.bytes)->dep_signal[0]=tokens[mode][2*((graph+1)*group-1)+1]->s;
        packets[mode][0].push_back(join);
      }
      require(packets[mode][0].size()==2*units+graphs && packets[mode][1].size()==2*units,"wrong boundary packet count");
      require(packets[mode][0].size()<queues[0].q->size && packets[mode][1].size()<queues[1].q->size,"queue capacity");
    }
  }
  ~Replay(){if(inflight) fail_inflight("destroying live graph replay");}
  void run(unsigned mode,bool profile,unsigned first_lane,Metrics& metric,uint64_t* times) {
    require(mode<3 && first_lane<2 && !inflight,"invalid run");
    for(auto& q:queues) H(hsa_amd_profiling_set_profiler_enabled(q.q,profile));
    uint64_t start=raw_ns();
    for(auto& s:finals) s->reset();
    for(auto& s:tokens[mode]) {
      s->reset();
      auto* words=reinterpret_cast<volatile uint64_t*>(s->s.handle);
      words[4]=0;words[5]=0;
    }
    // All previous launches are drained and no token has a concurrent owner.
    // These are uncached public fine-grained allocations. ROCr's x64 release
    // stores and ordinary doorbell path use SFENCE for WC publication. No CPU
    // readback/RMW is required in this diagnostic contract; exact values and
    // guards are checked after complete GPU drainage, outside primary timing.
    _mm_sfence();
    for(unsigned lane=0;lane<2;++lane) require(queues[lane].fits(packets[mode][lane].size()),"capacity before publication");
    const uint64_t prepared=raw_ns();Publication receipt[2]{};inflight=true;
    try {
      for(unsigned order=0;order<2;++order) {
        unsigned lane=order?1-first_lane:first_lane;
        receipt[lane]=queues[lane].publish(packets[mode][lane]);
      }
    } catch(...) {fail_inflight("publication failure");}
    const uint64_t published=raw_ns();
    finals.back()->wait();
    auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(15);
    for(unsigned lane=0;lane<2;++lane) while(hsa_queue_load_read_index_scacquire(queues[lane].q)<=receipt[lane].last) {
      if(queue_error.load() || std::chrono::steady_clock::now()>deadline) fail_inflight("drain timeout");
      __builtin_ia32_pause();
    }
    const uint64_t end=raw_ns();inflight=false;
    for(auto& s:tokens[mode]) {require(hsa_signal_load_scacquire(s->s)==0,"unique token completion mismatch");s->guards();}
    for(auto& s:finals) require(hsa_signal_load_scacquire(s->s)==0,"graph join completion mismatch");
    uint64_t earliest=std::numeric_limits<uint64_t>::max(),latest=0;
    if(profile) for(unsigned i=0;i<2*units;++i) {
      hsa_amd_profiling_dispatch_time_t t{};H(hsa_amd_profiling_get_dispatch_time(gpu,tokens[mode][i]->s,&t));
      require(t.start && t.end>=t.start,"invalid timestamps");
      times[2*i]=t.start;times[2*i+1]=t.end;earliest=std::min(earliest,t.start);latest=std::max(latest,t.end);
    }
    metric={double(prepared-start)/1000,double(published-prepared)/1000,double(end-start)/1000,double(end-published)/1000,
      profile?double(latest-earliest)*1e6/system_hz:0.0,system_hz,receipt[0].first,receipt[0].last,receipt[1].first,receipt[1].last,
      queues[0].q->id,queues[1].q->id,2*units+graphs};
  }
};
extern "C" int replay_create(const void* packets,unsigned group,unsigned units,void** result) {
  try {
    require(group && units && units%group==0,"invalid graph dimensions");
    H(hsa_init());gpu={};cpu={};pool={};gpu_count=0;queue_error.store(0);
    H(hsa_iterate_agents(agents,nullptr));require(gpu_count==1 && cpu.handle,"one visible GPU required");
    char name[64]{};H(hsa_agent_get_info(gpu,HSA_AGENT_INFO_NAME,name));require(std::string(name)=="gfx950","gfx950 required");
    H(hsa_amd_agent_iterate_memory_pools(cpu,pools,nullptr));require(pool.handle,"fine-grained kernarg pool required");
    *result=new Replay(packets,group,units);return 0;
  } catch(const std::exception& e) {std::fprintf(stderr,"CREATE_ERROR %s\n",e.what());return 1;}
}
extern "C" int replay_run(void* state,unsigned mode,unsigned profile,unsigned first_lane,Metrics* metric,uint64_t* times) {
  try {static_cast<Replay*>(state)->run(mode,profile,first_lane,*metric,times);return 0;}
  catch(const std::exception& e) {std::fprintf(stderr,"REPLAY_ERROR %s\n",e.what());return 1;}
}
extern "C" int replay_dump(void* state,const char* directory) {
  try {
    auto& r=*static_cast<Replay*>(state);require(!r.inflight,"live dump forbidden");std::string dir=directory;
    std::ofstream finals(dir+"/finals.csv");finals<<"index,handle\n";
    for(unsigned i=0;i<r.graphs;++i) finals<<i<<','<<r.finals[i]->s.handle<<'\n';require(bool(finals),"final receipt failed");
    for(unsigned mode=0;mode<3;++mode) {
      for(unsigned lane=0;lane<2;++lane) {
        std::ofstream f(dir+"/packets-m"+std::to_string(mode)+"-q"+std::to_string(lane)+".bin",std::ios::binary);
        const auto& p=r.packets[mode][lane];f.write(reinterpret_cast<const char*>(p.data()),p.size()*64);require(bool(f),"packet dump failed");
      }
      std::ofstream signals(dir+"/signals-m"+std::to_string(mode)+".csv");signals<<"index,handle,pointer,owner,owner_type,global_flags,host_base,agent_base,allocation_size\n";
      for(unsigned i=0;i<r.tokens[mode].size();++i) {
        auto& s=*r.tokens[mode][i];s.guards();signals<<i<<','<<s.s.handle<<','<<reinterpret_cast<uintptr_t>(s.pointer())<<','<<s.info.agentOwner.handle<<','<<unsigned(s.owner_type)<<','<<s.info.global_flags<<','<<reinterpret_cast<uintptr_t>(s.info.hostBaseAddress)<<','<<reinterpret_cast<uintptr_t>(s.info.agentBaseAddress)<<','<<s.info.sizeInBytes<<'\n';
      }
      require(bool(signals),"signal receipt failed");
    }
    return 0;
  } catch(const std::exception& e) {std::fprintf(stderr,"DUMP_ERROR %s\n",e.what());return 1;}
}
extern "C" int replay_destroy(void* state){delete static_cast<Replay*>(state);return hsa_shut_down()==HSA_STATUS_SUCCESS?0:1;}
