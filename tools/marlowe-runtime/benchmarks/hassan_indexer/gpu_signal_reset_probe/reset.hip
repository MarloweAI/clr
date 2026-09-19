#include <hip/hip_runtime.h>
#include <stdint.h>
// Runtime-helper prototype. Application Q/K kernels and graph DAG are unchanged.
extern "C" __global__ void reset_signal_values(const uint64_t* addresses, unsigned count) {
  unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<count) {
    volatile uint64_t* abi=reinterpret_cast<volatile uint64_t*>(addresses[i]);
    abi[1]=1; // value, offset8
    abi[4]=0; // profiling start, offset32
    abi[5]=0; // profiling end, offset40
  }
}
extern "C" int launch_signal_reset(const uint64_t* addresses,unsigned count,hipStream_t stream) {
  hipLaunchKernelGGL(reset_signal_values,dim3((count+63)/64),dim3(64),0,stream,addresses,count);
  return int(hipGetLastError());
}
