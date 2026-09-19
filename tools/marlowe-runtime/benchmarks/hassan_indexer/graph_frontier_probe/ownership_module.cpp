#include <hip/hip_runtime.h>
#ifndef ADDEND
#define ADDEND 1
#endif
extern "C" __global__ void write_value(int* output,int slot,int value,unsigned long long delay){
 auto start=wall_clock64();while(wall_clock64()-start<delay){}
 if(threadIdx.x==0)output[slot]=value+ADDEND;
}
