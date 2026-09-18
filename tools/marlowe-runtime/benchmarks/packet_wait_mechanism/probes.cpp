#include <hip/hip_runtime.h>
#include <stdint.h>
struct Sample { uint64_t start,end,last_nonzero_before,first_zero_after,seen,reads; };
__device__ __forceinline__ uint64_t tick() {
  uint64_t x; asm volatile("s_memrealtime %0\n\ts_waitcnt lgkmcnt(0)" : "=s"(x) :: "memory"); return x;
}
extern "C" __global__ void packet_probe(Sample* out, long long* target, uint64_t delay, unsigned role) {
  uint64_t begin=tick(),lower=0,upper=0,reads=0;long long value=-99;
  if(role==2) {
    do {
      uint64_t before=tick();
      value=__hip_atomic_load(target,__ATOMIC_ACQUIRE,__HIP_MEMORY_SCOPE_SYSTEM);
      asm volatile("s_waitcnt vmcnt(0)" ::: "memory");
      uint64_t after=tick();++reads;
      if(value==0) {upper=after;break;}
      lower=before;
      if(after-begin>delay)break;
      __builtin_amdgcn_s_sleep(1);
    } while(true);
  } else {
    while(tick()-begin<delay) {}
    if(role==3) {
      value=__hip_atomic_load(target,__ATOMIC_ACQUIRE,__HIP_MEMORY_SCOPE_SYSTEM);
      asm volatile("s_waitcnt vmcnt(0)" ::: "memory");
    }
  }
  uint64_t end=tick();
  *out={begin,end,lower,upper,uint64_t(value),reads};
}
