#include <hip/hip_runtime.h>
#include "probe_types.h"
__device__ __forceinline__ uint64_t tick() {
  uint64_t t;
  asm volatile("s_memrealtime %0\n\ts_waitcnt lgkmcnt(0)" : "=s"(t) :: "memory");
  return t;
}
extern "C" __global__ void layer_probe(LayerState* states, Sample* samples,
    uint64_t delay_ticks, uint64_t rendezvous_ticks, uint64_t epoch,
    uint32_t layer, uint32_t role, uint32_t blocks, uint32_t reserved) {
  extern __shared__ volatile uint32_t scratch[];
  scratch[threadIdx.x] = threadIdx.x + blockIdx.x + role;
  __syncthreads();
  if (threadIdx.x == 0) {
    uint64_t begin = tick(), saw = 0, input_ok = 1;
    if (layer) {
      uint64_t a = __hip_atomic_load(&states[layer-1].value[0], __ATOMIC_ACQUIRE, __HIP_MEMORY_SCOPE_SYSTEM);
      uint64_t b = __hip_atomic_load(&states[layer-1].value[1], __ATOMIC_ACQUIRE, __HIP_MEMORY_SCOPE_SYSTEM);
      uint64_t cq = __hip_atomic_load(&states[layer-1].completed[0], __ATOMIC_ACQUIRE, __HIP_MEMORY_SCOPE_SYSTEM);
      uint64_t ck = __hip_atomic_load(&states[layer-1].completed[1], __ATOMIC_ACQUIRE, __HIP_MEMORY_SCOPE_SYSTEM);
      input_ok = a == epoch * 1024 + (layer-1)*2+1 && b == epoch * 1024 + (layer-1)*2+2 &&
          cq == states[layer-1].expected[0] && ck == states[layer-1].expected[1];
    }
    if (blockIdx.x == 0) {
      __hip_atomic_store(&states[layer].started[role], epoch, __ATOMIC_RELEASE, __HIP_MEMORY_SCOPE_SYSTEM);
      do {
        saw = __hip_atomic_load(&states[layer].started[1-role], __ATOMIC_ACQUIRE, __HIP_MEMORY_SCOPE_SYSTEM) == epoch;
        if (saw || tick()-begin >= rendezvous_ticks) break;
        __builtin_amdgcn_s_sleep(1);
      } while (true);
    }
    while (tick()-begin < delay_ticks) __builtin_amdgcn_s_sleep(1);
    uint64_t value = epoch * 1024 + layer * 2 + role + 1;
    if (blockIdx.x == 0)
      __hip_atomic_store(&states[layer].value[role], value, __ATOMIC_RELEASE, __HIP_MEMORY_SCOPE_SYSTEM);
    uint64_t end = tick();
    samples[blockIdx.x] = {begin, end, saw, input_ok, value, blockIdx.x};
  }
  __syncthreads();
  // Dynamic LDS remains live throughout the measured work, with no cross-block dependency.
  if (scratch[threadIdx.x] != threadIdx.x + blockIdx.x + role)
    __builtin_trap();
  __syncthreads();
  if (threadIdx.x == 0)
    __hip_atomic_fetch_add(&states[layer].completed[role], uint64_t(1), __ATOMIC_RELEASE, __HIP_MEMORY_SCOPE_SYSTEM);
}
