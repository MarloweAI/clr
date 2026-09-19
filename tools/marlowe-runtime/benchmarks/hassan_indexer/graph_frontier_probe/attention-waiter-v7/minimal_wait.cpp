// The core reproduction: no host transfers, frameworks, or model state.
// hipcc -O3 -std=c++17 minimal_wait.cpp -o minimal_wait
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#define CHECK(call) do { auto check_status = (call); if (check_status != hipSuccess) { \
  std::fprintf(stderr, "%s: %s\n", #call, hipGetErrorString(check_status)); std::exit(1); \
} } while (0)
__global__ void increment(unsigned* value) { ++*value; }
int main() {
  int count;
  CHECK(hipGetDeviceCount(&count));
  if (count != 1) { std::fprintf(stderr, "Require one allocated GPU\n"); return 1; }
  std::ifstream maps("/proc/self/maps");
  for (std::string line; std::getline(maps,line);)
    if (line.find("libamdhip64")!=std::string::npos || line.find("libhsa-runtime64")!=std::string::npos)
      std::fprintf(stderr,"LIBRARY %s\n",line.c_str());
  hipStream_t compute, side;
  CHECK(hipStreamCreateWithFlags(&compute, hipStreamNonBlocking));
  CHECK(hipStreamCreateWithFlags(&side, hipStreamNonBlocking));
  hipEvent_t begin, end;
  CHECK(hipEventCreate(&begin));
  CHECK(hipEventCreate(&end));
  unsigned* value;
  CHECK(hipMalloc(&value, sizeof(unsigned)));
  hipGraph_t graph;
  hipGraphExec_t executable;
  CHECK(hipStreamBeginCapture(compute, hipStreamCaptureModeGlobal));
  for (int i = 0; i < 2048; ++i) increment<<<1, 1, 0, compute>>>(value);
  CHECK(hipStreamEndCapture(compute, &graph));
  CHECK(hipGraphInstantiate(&executable, graph, nullptr, nullptr, 0));
  const char* names[] = {"alone", "pending_wait", "ready_wait"};
  std::puts("block,case,gpu_us,pending,correct");
  for (int block = -1; block < 5; ++block) {
    for (int j = 0; j < 3; ++j) {
      int mode = (j + block + 3) % 3;
      for (int repeat = 0; repeat < 8; ++repeat) {
        CHECK(hipMemsetAsync(value, 0, sizeof(unsigned), compute));
        CHECK(hipStreamSynchronize(compute));
        CHECK(hipEventRecord(begin, compute));
        CHECK(hipGraphLaunch(executable, compute));
        CHECK(hipEventRecord(end, compute));
        bool pending = false;
        if (mode == 1) {
          auto status = hipEventQuery(end);
          if (status != hipSuccess && status != hipErrorNotReady) CHECK(status);
          pending = status == hipErrorNotReady;
          CHECK(hipStreamWaitEvent(side, end, 0));
        }
        CHECK(hipEventSynchronize(end));
        if (mode == 2) CHECK(hipStreamWaitEvent(side, end, 0));
        CHECK(hipStreamSynchronize(side)); // No dependency survives into next trial.
        float ms;
        CHECK(hipEventElapsedTime(&ms, begin, end));
        unsigned result;
        CHECK(hipMemcpy(&result, value, sizeof(result), hipMemcpyDeviceToHost));
        if (result != 2048) return 2;
        if (block >= 0) std::printf("%d,%s,%.3f,%d,1\n", block, names[mode], ms*1000, pending);
      }
    }
  }
  CHECK(hipGraphExecDestroy(executable));
  CHECK(hipGraphDestroy(graph));
  CHECK(hipEventDestroy(begin)); CHECK(hipEventDestroy(end));
  CHECK(hipStreamDestroy(compute)); CHECK(hipStreamDestroy(side));
  CHECK(hipFree(value));
}
