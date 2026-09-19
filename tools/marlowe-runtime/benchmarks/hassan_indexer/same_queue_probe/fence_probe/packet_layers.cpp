#include <hsa/hsa.h>
#include <hsa/hsa_ext_amd.h>
#include "probe_types.h"
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
  explicit Memory(size_t n) {
    H(hsa_amd_memory_pool_allocate(pool,n,0,&p));
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
  void wait() {
    auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(15);
    while(hsa_signal_load_scacquire(s)!=0) {
      if(queue_error.load() || std::chrono::steady_clock::now()>deadline)
        fail_inflight("completion timeout or queue error");
      std::this_thread::sleep_for(std::chrono::microseconds(20));
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
uint64_t kernel_object;
uint32_t private_size,static_group_size,kernarg_size,kernarg_align;
Packet dispatch(void* args,unsigned blocks,unsigned lds,bool ordered,unsigned acquire,unsigned release) {
  hsa_kernel_dispatch_packet_t p{};
  p.header=(HSA_PACKET_TYPE_KERNEL_DISPATCH<<HSA_PACKET_HEADER_TYPE) |
      (unsigned(ordered)<<HSA_PACKET_HEADER_BARRIER) |
      (acquire<<HSA_PACKET_HEADER_SCACQUIRE_FENCE_SCOPE) |
      (release<<HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE);
  p.setup=1<<HSA_KERNEL_DISPATCH_PACKET_SETUP_DIMENSIONS;
  p.workgroup_size_x=128; p.workgroup_size_y=p.workgroup_size_z=1;
  p.grid_size_x=blocks*128; p.grid_size_y=p.grid_size_z=1;
  p.private_segment_size=private_size; p.group_segment_size=static_group_size+lds;
  p.kernel_object=kernel_object; p.kernarg_address=args;
  Packet out; std::memcpy(out.bytes,&p,64); return out;
}
void raw(const std::string& path,const void* p,size_t bytes) {
  std::ofstream file(path,std::ios::binary); file.write(static_cast<const char*>(p),bytes);
  require(bool(file),"artifact write failed");
}
int main(int argc,char** argv) {
  try {
    require(argc==3,"usage: packet_layers probes.hsaco output-directory");
    std::string out=argv[2]; H(hsa_init()); H(hsa_iterate_agents(agents,nullptr));
    require(gpu_count==1 && cpu.handle,"require exactly one GPU and CPU agent");
    H(hsa_amd_agent_iterate_memory_pools(cpu,pools,nullptr)); require(pool.handle,"no kernarg pool");
    char name[64]{}; uint64_t frequency; uint32_t cu; hsa_profile_t profile;
    H(hsa_agent_get_info(gpu,HSA_AGENT_INFO_NAME,name));
    H(hsa_agent_get_info(gpu,HSA_AGENT_INFO_PROFILE,&profile));
    H(hsa_agent_get_info(gpu,(hsa_agent_info_t)HSA_AMD_AGENT_INFO_TIMESTAMP_FREQUENCY,&frequency));
    H(hsa_agent_get_info(gpu,(hsa_agent_info_t)HSA_AMD_AGENT_INFO_COMPUTE_UNIT_COUNT,&cu));
    require(std::string(name)=="gfx950" && cu==256,"requires full MI355X agent");
    int fd=open(argv[1],O_RDONLY); require(fd>=0,"code object open failed");
    hsa_code_object_reader_t reader{}; hsa_executable_t exec{};
    H(hsa_code_object_reader_create_from_file(fd,&reader));
    H(hsa_executable_create_alt(profile,HSA_DEFAULT_FLOAT_ROUNDING_MODE_DEFAULT,nullptr,&exec));
    H(hsa_executable_load_agent_code_object(exec,gpu,reader,nullptr,nullptr)); H(hsa_executable_freeze(exec,nullptr));
    hsa_executable_symbol_t sym{}; H(hsa_executable_get_symbol_by_name(exec,"layer_probe.kd",&gpu,&sym));
    H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_OBJECT,&kernel_object));
    H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_PRIVATE_SEGMENT_SIZE,&private_size));
    H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_GROUP_SEGMENT_SIZE,&static_group_size));
    H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_KERNARG_SEGMENT_SIZE,&kernarg_size));
    H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_KERNARG_SEGMENT_ALIGNMENT,&kernarg_align));
    size_t stride=(std::max<size_t>(kernarg_size,sizeof(Args))+255)&~size_t(255);
    require(kernarg_align<=256 && !private_size && !static_group_size,"unexpected probe resources");
    std::ofstream meta(out+"/device.json");
    meta<<"{\"agent\":\""<<name<<"\",\"compute_units\":"<<cu<<",\"timestamp_hz\":"<<frequency
        <<",\"kernarg_size\":"<<kernarg_size<<",\"kernarg_align\":"<<kernarg_align
        <<",\"kernel_object\":"<<kernel_object<<",\"private_bytes\":"<<private_size
        <<",\"static_group_bytes\":"<<static_group_size<<"}\n"; meta.close();
    {
      Queue queues[2];
      std::ifstream maps("/proc/self/maps"); std::ofstream mapped(out+"/maps.txt"); mapped<<maps.rdbuf(); mapped.close();
      struct Config { std::string name; unsigned a0,r0,a1,r1; bool first_ordered,serial,two_queues; };
      std::vector<Config> configs;
      for(unsigned release:{2u,1u,0u}) for(unsigned acquire:{2u,1u,0u})
        configs.push_back({"edge_r"+std::to_string(release)+"_a"+std::to_string(acquire),2,release,acquire,2,true,false,false});
      configs.push_back({"agent_pair",1,1,1,1,true,false,false});
      configs.push_back({"none_pair",0,0,0,0,true,false,false});
      configs.push_back({"none_pair_first_unordered",0,0,0,0,false,false,false});
      configs.push_back({"agent_pair_first_unordered",1,1,1,1,false,false,false});
      configs.push_back({"system_pair_first_unordered",2,2,2,2,false,false,false});
      configs.push_back({"serial_system",2,2,2,2,true,true,false});
      configs.push_back({"serial_none",0,0,0,0,true,true,false});
      configs.push_back({"two_queue_system",2,2,2,2,true,false,true});
      std::ofstream csv(out+"/trials.csv");
      csv<<"id,round,case,geometry,reverse,epoch,blocks_q,blocks_k,lds,a0,r0,a1,r1,first_ordered,serial,two_queues,queue0,queue1,first0,last0,first1,last1,doorbells,overlap,trace,states,packets0,packets1,correct\n";
      unsigned id=0;
      for(unsigned round=0;round<4;++round) for(unsigned geometry=0;geometry<2;++geometry)
      for(unsigned reverse=0;reverse<2;++reverse) for(unsigned index=0;index<configs.size();++index) {
        const Config& config=configs[round%2?configs.size()-index-1:index];
        unsigned blocks[2]={geometry?256u:1u,geometry?24u:1u};
        unsigned lds=geometry?61440:512;
        uint64_t epoch=id+1;
        size_t samples_count=blocks[0]+blocks[1];
        Memory state_mem(sizeof(LayerState)),sample_mem(samples_count*sizeof(Sample)),arg_mem(2*stride);
        auto* states=static_cast<LayerState*>(state_mem.p);
        auto* samples=static_cast<Sample*>(sample_mem.p);
        states->expected[0]=blocks[0]; states->expected[1]=blocks[1];
        Signal done[2], gate;
        std::vector<Packet> packets[2];
        // Ordered SYSTEM entry/exit barriers hold host publication and final lifetime
        // constant while the critical inter-kernel fences are varied.
        packets[0].push_back(boundary(true,{},config.two_queues?gate.s:hsa_signal_t{}));
        if(config.two_queues) packets[1].push_back(boundary(true,{},gate.s));
        for(unsigned position=0;position<2;++position) {
          unsigned role=position^reverse;
          void* args=static_cast<char*>(arg_mem.p)+position*stride;
          uint64_t delay=frequency*(1500+500*((role+round)%2))/1000000;
          Args values{states,samples+(role?blocks[0]:0),delay,frequency/1000,epoch,0,role,blocks[role],0};
          std::memcpy(args,&values,sizeof(values));
          unsigned which=config.two_queues?position:0;
          bool ordered=position==0?config.first_ordered:config.serial;
          packets[which].push_back(dispatch(args,blocks[role],lds,ordered,
              position==0?config.a0:config.a1,position==0?config.r0:config.r1));
        }
        packets[0].push_back(boundary(false,done[0].s));
        if(config.two_queues) packets[1].push_back(boundary(false,done[1].s));
        std::string prefix=out+"/trial-"+std::to_string(id);
        raw(prefix+"-packets0.bin",packets[0].data(),packets[0].size()*64);
        if(config.two_queues) raw(prefix+"-packets1.bin",packets[1].data(),packets[1].size()*64);
        require(queues[0].fits(packets[0].size()) &&
            (!config.two_queues || queues[1].fits(packets[1].size())),"capacity before any publication");
        Publication receipts[2]{};
        receipts[0]=queues[0].publish(packets[0]);
        if(config.two_queues) {
          try { receipts[1]=queues[1].publish(packets[1]); }
          catch (...) { fail_inflight("second queue publication failed after first was published"); }
        }
        if(config.two_queues) {
          std::this_thread::sleep_for(std::chrono::microseconds(200));
          hsa_signal_store_screlease(gate.s,0);
        }
        done[0].wait(); if(config.two_queues) done[1].wait();
        bool overlap=samples[0].saw_peer && samples[blocks[0]].saw_peer;
        require(!config.serial || !overlap,"serialized arm falsely proved concurrency");
        for(unsigned role=0;role<2;++role)
          require(states->value[role]==epoch*1024+role+1 && states->completed[role]==blocks[role],"final output/count mismatch");
        for(size_t i=0;i<samples_count;++i)
          require(samples[i].start && samples[i].end>=samples[i].start && samples[i].input_ok,"invalid GPU sample");
        raw(prefix+"-samples.bin",samples,samples_count*sizeof(Sample));
        raw(prefix+"-states.bin",states,sizeof(LayerState));
        csv<<id<<','<<round<<','<<config.name<<','<<(geometry?"qk_geometry":"one_block")
          <<','<<reverse<<','<<epoch<<','<<blocks[0]<<','<<blocks[1]<<','<<lds<<','
          <<config.a0<<','<<config.r0<<','<<config.a1<<','<<config.r1<<','<<config.first_ordered<<','
          <<config.serial<<','<<config.two_queues<<','<<queues[0].q->id<<','<<(config.two_queues?queues[1].q->id:0)
          <<','<<receipts[0].first<<','<<receipts[0].last<<','<<receipts[1].first<<','<<receipts[1].last
          <<','<<(config.two_queues?2:1)<<','<<overlap<<",trial-"<<id<<"-samples.bin,trial-"<<id
          <<"-states.bin,trial-"<<id<<"-packets0.bin,";
        if(config.two_queues) csv<<"trial-"<<id<<"-packets1.bin";
        csv<<",1\n"; csv.flush();
        std::cout<<"PROGRESS trial="<<id<<" case="<<config.name<<" geometry="<<geometry
          <<" concurrent="<<overlap<<std::endl;
        ++id;
      }
    }
    H(hsa_executable_destroy(exec)); H(hsa_code_object_reader_destroy(reader)); close(fd); H(hsa_shut_down());
    std::cout<<"COMPLETE\n"; return 0;
  } catch(const std::exception& e) { std::cerr<<"ERROR "<<e.what()<<std::endl; return 1; }
}
