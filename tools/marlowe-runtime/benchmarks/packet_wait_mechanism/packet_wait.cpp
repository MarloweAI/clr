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
#include <fcntl.h>
#include <unistd.h>
#define H(call) do {auto e=(call);if(e!=HSA_STATUS_SUCCESS){const char* t=nullptr;hsa_status_string(e,&t);throw std::runtime_error(std::string(#call)+": "+(t?t:"unknown"));}} while(0)
struct Sample {uint64_t start,end,last_nonzero_before,first_zero_after,seen,reads;};
struct Args {Sample* out;long long* target;uint64_t delay;unsigned role;unsigned pad;};
static_assert(sizeof(Sample)==48 && sizeof(Args)==32);
hsa_agent_t gpu{},cpu{};hsa_amd_memory_pool_t pool{};unsigned gpu_count=0;std::atomic<int> queue_error{0};
hsa_status_t agents(hsa_agent_t a,void*) {hsa_device_type_t t;H(hsa_agent_get_info(a,HSA_AGENT_INFO_DEVICE,&t));if(t==HSA_DEVICE_TYPE_GPU){gpu=a;++gpu_count;}if(t==HSA_DEVICE_TYPE_CPU&&!cpu.handle)cpu=a;return HSA_STATUS_SUCCESS;}
hsa_status_t pools(hsa_amd_memory_pool_t p,void*) {hsa_amd_segment_t seg;H(hsa_amd_memory_pool_get_info(p,HSA_AMD_MEMORY_POOL_INFO_SEGMENT,&seg));if(seg!=HSA_AMD_SEGMENT_GLOBAL)return HSA_STATUS_SUCCESS;uint32_t flags;bool allowed;H(hsa_amd_memory_pool_get_info(p,HSA_AMD_MEMORY_POOL_INFO_GLOBAL_FLAGS,&flags));H(hsa_amd_memory_pool_get_info(p,HSA_AMD_MEMORY_POOL_INFO_RUNTIME_ALLOC_ALLOWED,&allowed));if(allowed&&(flags&HSA_AMD_MEMORY_POOL_GLOBAL_FLAG_FINE_GRAINED)&&(flags&HSA_AMD_MEMORY_POOL_GLOBAL_FLAG_KERNARG_INIT))pool=p;return HSA_STATUS_SUCCESS;}
struct Memory {void* p=nullptr;Memory(size_t n,uint32_t flags=0){H(hsa_amd_memory_pool_allocate(pool,n,flags,&p));H(hsa_amd_agents_allow_access(1,&gpu,nullptr,p));std::memset(p,0,n);}~Memory(){if(p)hsa_amd_memory_pool_free(p);}};
[[noreturn]] void fail_inflight(const char* message){std::fprintf(stderr,"INFLIGHT_FAILURE %s; process exit without reclaiming live queue resources\n",message);std::fflush(stderr);std::_Exit(2);}
struct Signal {hsa_signal_t s{};Signal(int64_t v){H(hsa_amd_signal_create(v,0,nullptr,HSA_AMD_SIGNAL_IPC,&s));}~Signal(){if(s.handle)hsa_signal_destroy(s);}void wait(){auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);while(hsa_signal_load_scacquire(s)!=0){if(queue_error.load()||std::chrono::steady_clock::now()>deadline)fail_inflight("completion timeout or queue error");std::this_thread::sleep_for(std::chrono::microseconds(20));}}long long* pointer(){volatile hsa_signal_value_t* p=nullptr;H(hsa_amd_signal_value_pointer(s,&p));return reinterpret_cast<long long*>(const_cast<hsa_signal_value_t*>(p));}};
struct Queue {hsa_queue_t* q=nullptr;Queue(){H(hsa_queue_create(gpu,4096,HSA_QUEUE_TYPE_SINGLE,[](hsa_status_t e,hsa_queue_t*,void*){queue_error.store(int(e));},nullptr,UINT32_MAX,UINT32_MAX,&q));}~Queue(){if(q)hsa_queue_destroy(q);}void publish(const void* src,size_t count){if(!count)return;uint64_t first=hsa_queue_add_write_index_relaxed(q,count);if(first+count-hsa_queue_load_read_index_scacquire(q)>q->size)fail_inflight("queue overrun");for(size_t i=0;i<count;++i){auto* dst=(char*)q->base_address+64*((first+i)&(q->size-1));const auto* p=(const char*)src+64*i;uint16_t header;std::memcpy(&header,p,2);std::memcpy(dst+2,p+2,62);__atomic_store_n(reinterpret_cast<uint16_t*>(dst),header,__ATOMIC_RELEASE);}hsa_signal_store_screlease(q->doorbell_signal,first+count-1);}};
struct alignas(64) Packet {unsigned char b[64]{};};static_assert(sizeof(Packet)==64);
constexpr uint16_t hdr(unsigned type,bool barrier=true,bool system=true){return (type<<HSA_PACKET_HEADER_TYPE)|(unsigned(barrier)<<HSA_PACKET_HEADER_BARRIER)|((system?HSA_FENCE_SCOPE_SYSTEM:HSA_FENCE_SCOPE_NONE)<<HSA_PACKET_HEADER_SCACQUIRE_FENCE_SCOPE)|((system?HSA_FENCE_SCOPE_SYSTEM:HSA_FENCE_SCOPE_NONE)<<HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE);}
Packet barrier(hsa_signal_t dep={},bool order=true,bool system=true){hsa_barrier_and_packet_t p{};p.header=hdr(HSA_PACKET_TYPE_BARRIER_AND,order,system);p.dep_signal[0]=dep;Packet out;std::memcpy(out.b,&p,64);return out;}
Packet native(long long* target,uint32_t* ib){uintptr_t address=reinterpret_cast<uintptr_t>(target),base=reinterpret_cast<uintptr_t>(ib);if((address&3)||(base&3)||(base>>48))throw std::runtime_error("native pointer range");ib[0]=0xc0053c00;ib[1]=3|(1<<4);ib[2]=uint32_t(address);ib[3]=uint32_t(address>>32);ib[4]=0;ib[5]=0xffffffff;ib[6]=4;
 struct Vendor {uint16_t header,format;uint32_t jump[4],remain,reserved[8];hsa_signal_t completion;};static_assert(sizeof(Vendor)==64);Vendor p{};p.header=hdr(HSA_PACKET_TYPE_VENDOR_SPECIFIC,false,false);p.format=1;p.jump[0]=0xc0023f00;p.jump[1]=uint32_t(base)&0xfffffffc;p.jump[2]=uint32_t(base>>32)&0xffff;p.jump[3]=7|(1<<23);p.remain=0xa;Packet out;std::memcpy(out.b,&p,64);return out;}
uint64_t object;uint32_t private_size,group_size,kernarg_size,kernarg_align;size_t stride;
Packet dispatch(void* args,hsa_signal_t done={}){hsa_kernel_dispatch_packet_t p{};p.header=hdr(HSA_PACKET_TYPE_KERNEL_DISPATCH);p.setup=1<<HSA_KERNEL_DISPATCH_PACKET_SETUP_DIMENSIONS;p.workgroup_size_x=p.workgroup_size_y=p.workgroup_size_z=1;p.grid_size_x=p.grid_size_y=p.grid_size_z=1;p.private_segment_size=private_size;p.group_segment_size=group_size;p.kernel_object=object;p.kernarg_address=args;p.completion_signal=done;Packet out;std::memcpy(out.b,&p,64);return out;}
int main(int argc,char** argv){try{
 if(argc!=3)throw std::runtime_error("usage: packet_wait probes.hsaco output-directory");std::string out=argv[2];H(hsa_init());H(hsa_iterate_agents(agents,nullptr));if(gpu_count!=1||!cpu.handle)throw std::runtime_error("require exactly one GPU and CPU agent");H(hsa_amd_agent_iterate_memory_pools(cpu,pools,nullptr));if(!pool.handle)throw std::runtime_error("no CPU fine-grained kernarg pool");
 char name[64]{};uint64_t frequency;hsa_profile_t profile;H(hsa_agent_get_info(gpu,HSA_AGENT_INFO_NAME,name));H(hsa_agent_get_info(gpu,HSA_AGENT_INFO_PROFILE,&profile));H(hsa_agent_get_info(gpu,(hsa_agent_info_t)HSA_AMD_AGENT_INFO_TIMESTAMP_FREQUENCY,&frequency));if(std::string(name)!="gfx950")throw std::runtime_error("native encoding only scoped to gfx950");
 int fd=open(argv[1],O_RDONLY);if(fd<0)throw std::runtime_error("code object open");hsa_code_object_reader_t reader{};hsa_executable_t exec{};H(hsa_code_object_reader_create_from_file(fd,&reader));H(hsa_executable_create_alt(profile,HSA_DEFAULT_FLOAT_ROUNDING_MODE_DEFAULT,nullptr,&exec));H(hsa_executable_load_agent_code_object(exec,gpu,reader,nullptr,nullptr));H(hsa_executable_freeze(exec,nullptr));hsa_executable_symbol_t sym{};H(hsa_executable_get_symbol_by_name(exec,"packet_probe.kd",&gpu,&sym));H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_OBJECT,&object));H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_PRIVATE_SEGMENT_SIZE,&private_size));H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_GROUP_SEGMENT_SIZE,&group_size));H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_KERNARG_SEGMENT_SIZE,&kernarg_size));H(hsa_executable_symbol_get_info(sym,HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_KERNARG_SEGMENT_ALIGNMENT,&kernarg_align));stride=(std::max<size_t>(kernarg_size,sizeof(Args))+255)&~size_t(255);if(kernarg_align>256)throw std::runtime_error("kernarg alignment");
 std::ofstream meta(out+"/device.json");meta<<"{\"agent\":\""<<name<<"\",\"timestamp_hz\":"<<frequency<<",\"kernarg_size\":"<<kernarg_size<<",\"kernarg_align\":"<<kernarg_align<<",\"private_bytes\":"<<private_size<<",\"group_bytes\":"<<group_size<<"}\n";meta.close();
 {Queue queues[4];for(unsigned i=0;i<4;++i)std::cerr<<"QUEUE slot="<<i<<" id="<<queues[i].q->id<<" size="<<queues[i].q->size<<"\n";
 std::ifstream maps("/proc/self/maps");std::ofstream mapped(out+"/maps.txt");mapped<<maps.rdbuf();mapped.close();
 std::ofstream csv(out+"/trials.csv");csv<<"id,round,trial,case,mode,independent,observer,producer_count,independent_count,delay_ticks,trace,correct\n";
 std::ofstream addresses(out+"/addresses.csv");addresses<<"id,case,mode,target,ib,ib_bytes,ib_flags,data,data_bytes,args,args_bytes,producer_queue,producer_read,producer_write,consumer_queue,consumer_read,consumer_write\n";
 const char* cases[]={"ready","delayed","chain32","chain2048"};const char* modes[]={"none","barrier","nop_barrier","native_barrier"};unsigned id=0;
 for(unsigned round=0;round<2;++round)for(unsigned config=0;config<4;++config)for(unsigned independent=0;independent<2;++independent)for(unsigned observer=0;observer<2;++observer)for(unsigned trial=0;trial<3;++trial)for(unsigned order=0;order<4;++order){unsigned mode=(order+round+trial)%4;bool ready=config==0;size_t n=config==3?2048:config==2?32:1,ni=independent?256:0;uint64_t delay=config==1?frequency/50000:0;
  Signal gate(1),producer_done(1),consumer_done(1),independent_done(1),observer_done(1),ready_signal(0);Signal& target=ready?ready_signal:producer_done;auto* target_ptr=target.pointer();size_t total=n+1+ni+observer;Memory data(total*sizeof(Sample)),args(total*stride),ib(64,HSA_AMD_MEMORY_POOL_EXECUTABLE_FLAG);auto* samples=(Sample*)data.p;size_t arg_index=0;
  auto launch=[&](size_t index,unsigned role,uint64_t ticks,hsa_signal_t done={}){void* a=(char*)args.p+stride*arg_index++;Args x{samples+index,target_ptr,ticks,role,0};std::memcpy(a,&x,sizeof(x));return dispatch(a,done);};
  std::vector<Packet> p{barrier(gate.s)},c{barrier(gate.s)},ind,obs;
  for(size_t i=0;i<n;++i)p.push_back(launch(i,1,delay,i==n-1?producer_done.s:hsa_signal_t{}));
  if(mode==2)c.push_back(barrier({},false,false));if(mode==3)c.push_back(native(target_ptr,(uint32_t*)ib.p));if(mode)c.push_back(barrier(target.s));c.push_back(launch(n,3,0,consumer_done.s));
  if(ni){ind.push_back(barrier(gate.s));for(size_t i=0;i<ni;++i)ind.push_back(launch(n+1+i,0,0,i==ni-1?independent_done.s:hsa_signal_t{}));}
  if(observer){obs.push_back(barrier(gate.s));obs.push_back(launch(n+1+ni,2,frequency/2,observer_done.s));}
  if(arg_index!=total)throw std::runtime_error("argument count");
  auto* pq=queues[round%4].q;auto* cq=queues[(round+1)%4].q;
  addresses<<id<<','<<cases[config]<<','<<modes[mode]<<','<<(void*)target_ptr<<','<<ib.p<<",64,"<<HSA_AMD_MEMORY_POOL_EXECUTABLE_FLAG<<','<<data.p<<','<<total*sizeof(Sample)<<','<<args.p<<','<<total*stride<<','<<pq->id<<','<<hsa_queue_load_read_index_scacquire(pq)<<','<<hsa_queue_load_write_index_scacquire(pq)<<','<<cq->id<<','<<hsa_queue_load_read_index_scacquire(cq)<<','<<hsa_queue_load_write_index_scacquire(cq)<<'\n';addresses.flush();
  if(mode==3&&trial==0&&!independent&&!observer){std::ifstream live_maps("/proc/self/maps");std::ofstream saved(out+"/maps-before-"+std::to_string(id)+".txt");saved<<live_maps.rdbuf();}
  std::fprintf(stderr,"TRIAL_BEGIN id=%u case=%s mode=%s target=%p ib=%p data=%p args=%p\n",id,cases[config],modes[mode],(void*)target_ptr,ib.p,data.p,args.p);std::fflush(stderr);
  queues[(round+0)%4].publish(p.data(),p.size());queues[(round+1)%4].publish(c.data(),c.size());if(ni)queues[(round+2)%4].publish(ind.data(),ind.size());if(observer)queues[(round+3)%4].publish(obs.data(),obs.size());
  std::this_thread::sleep_for(std::chrono::microseconds(200));hsa_signal_store_screlease(gate.s,0);
  producer_done.wait();consumer_done.wait();if(ni)independent_done.wait();if(observer)observer_done.wait();
  for(size_t i=0;i<total;++i)if(!samples[i].start||samples[i].end<samples[i].start)throw std::runtime_error("invalid sample");
  for(size_t i=1;i<n;++i)if(samples[i].start<samples[i-1].end)throw std::runtime_error("producer timestamp order");
  for(size_t i=n+2;i<n+1+ni;++i)if(samples[i].start<samples[i-1].end)throw std::runtime_error("independent timestamp order");
  if(mode&&samples[n].seen!=0)throw std::runtime_error("consumer ran before readiness");
  if(observer&&samples[total-1].seen!=0)throw std::runtime_error("observer did not see readiness");
  std::string file="trace-"+std::to_string(id)+".bin";std::ofstream raw(out+"/"+file,std::ios::binary);raw.write((const char*)data.p,total*sizeof(Sample));raw.close();
  csv<<id<<','<<round<<','<<trial<<','<<cases[config]<<','<<modes[mode]<<','<<independent<<','<<observer<<','<<n<<','<<ni<<','<<delay<<','<<file<<",1\n";csv.flush();++id;
 }
 std::cout<<"TRIALS "<<id<<" COMPLETE\n";
 }
 H(hsa_executable_destroy(exec));H(hsa_code_object_reader_destroy(reader));close(fd);H(hsa_shut_down());return 0;
 }catch(const std::exception& e){std::cerr<<"ERROR "<<e.what()<<"\n";return 1;}}
