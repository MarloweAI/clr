#pragma once
#include <dlfcn.h>
#include <hip/hip_runtime.h>
#include <rocblas/rocblas.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <functional>
#include <numeric>
#include <string>
#include <vector>
#define HIP(x)                                                      \
  do {                                                              \
    auto hip_status_result = (x);                                   \
    if (hip_status_result != hipSuccess) {                          \
      fprintf(stderr, "HIP %s:%d %s: %s\n", __FILE__, __LINE__, #x, \
              hipGetErrorString(hip_status_result));                \
      std::exit(2);                                                 \
    }                                                               \
  } while (0)
#define BLAS(x)                                                                                \
  do {                                                                                         \
    auto blas_status_result = (x);                                                             \
    if (blas_status_result != rocblas_status_success) {                                        \
      fprintf(stderr, "BLAS %s:%d %s: %d\n", __FILE__, __LINE__, #x, int(blas_status_result)); \
      std::exit(2);                                                                            \
    }                                                                                          \
  } while (0)
inline void require(bool ok, const char* why) {
  if (!ok) {
    fprintf(stderr, "FAILED %s\n", why);
    std::exit(3);
  }
}
template <class T>
struct Device {
  T* p = nullptr;
  size_t n = 0;
  explicit Device(size_t size) : n(size) { HIP(hipMalloc(&p, n * sizeof(T))); }
  ~Device() {
    if (p) HIP(hipFree(p));
  }
  Device(const Device&) = delete;
  Device& operator=(const Device&) = delete;
  operator T*() const { return p; }
  size_t bytes() const { return n * sizeof(T); }
};
struct Pinned {
  unsigned char *host = nullptr, *device = nullptr;
  size_t n;
  explicit Pinned(size_t bytes) : n(bytes) {
    HIP(hipHostMalloc(&host, n, hipHostMallocMapped));
    HIP(hipHostGetDevicePointer(reinterpret_cast<void**>(&device), host, 0));
  }
  ~Pinned() {
    if (host) HIP(hipHostFree(host));
  }
  Pinned(const Pinned&) = delete;
};
struct Event {
  hipEvent_t e{};
  explicit Event(bool timing = false) {
    HIP(hipEventCreateWithFlags(&e, timing ? hipEventDefault : hipEventDisableTiming));
  }
  ~Event() { HIP(hipEventDestroy(e)); }
  Event(const Event&) = delete;
  operator hipEvent_t() const { return e; }
  void record(hipStream_t s) { HIP(hipEventRecord(e, s)); }
  void wait(hipStream_t s) { HIP(hipStreamWaitEvent(s, e, 0)); }
};
struct Context {
  hipStream_t s[4]{};
  hipDeviceProp_t prop{};
  int trials = 12;
  Context() {
    int n;
    HIP(hipGetDeviceCount(&n));
    require(n == 1, "exactly one allocated GPU required");
    HIP(hipGetDeviceProperties(&prop, 0));
    require(prop.warpSize == 64, "wave64 required");
    const char* mode = getenv("LLM_RUNTIME_MODE");
    require(mode, "runtime mode receipt required");
    if (std::string(mode) == "experimental") {
      using Marker = unsigned (*)(unsigned, unsigned);
      using Wait = unsigned (*)(unsigned, unsigned, unsigned);
      auto marker = (Marker)dlsym(RTLD_DEFAULT, "marlowe_hip_graph_marker_control");
      auto wait = (Wait)dlsym(RTLD_DEFAULT, "marlowe_hip_native_wait_control");
      require(marker && wait, "experimental control APIs missing");
      require(marker(2, 0) == 2, "marker mode2");
      require(wait(1, 0, 4) == 1025, "native wait policy1 interval4");
      fprintf(stderr, "EXPERIMENTAL marker=%u wait=%u\n", marker(~0u, 0), wait(~0u, 0, 0));
    }
    for (auto& stream : s) HIP(hipStreamCreateWithFlags(&stream, hipStreamNonBlocking));
    if (getenv("LLM_TRIALS")) trials = std::stoi(getenv("LLM_TRIALS"));
    require(trials >= 4, "at least4 trials");
    char pci[64];
    HIP(hipDeviceGetPCIBusId(pci, 64, 0));
    fprintf(stderr,
            "DEVICE name=%s pci=%s CUs=%d wave=%d concurrent=%d async_engines=%d memory=%zu "
            "mode=%s wait=%s\n",
            prop.name, pci, prop.multiProcessorCount, prop.warpSize, prop.concurrentKernels,
            prop.asyncEngineCount, prop.totalGlobalMem, mode, getenv("GPU_NATIVE_EVENT_WAIT"));
    print_maps();
  }
  static void print_maps() {
    std::ifstream in("/proc/self/maps");
    for (std::string l; std::getline(in, l);)
      if (l.find("libamdhip64") != std::string::npos ||
          l.find("libhsa-runtime64") != std::string::npos ||
          l.find("librocblas") != std::string::npos)
        fprintf(stderr, "LIBRARY %s\n", l.c_str());
  }
  ~Context() {
    HIP(hipDeviceSynchronize());
    for (auto stream : s) HIP(hipStreamDestroy(stream));
  }
};
struct Executable {
  std::function<void()> enqueue;
  hipGraph_t graph{};
  hipGraphExec_t exec{};
  hipStream_t root;
  bool captured;
  Executable(std::function<void()> fn, hipStream_t r, bool capture)
      : enqueue(std::move(fn)), root(r), captured(capture) {
    // Prime library workspaces and lazy kernels outside capture/timing.
    enqueue();
    HIP(hipGetLastError());
    HIP(hipDeviceSynchronize());
    if (captured) {
      HIP(hipStreamBeginCapture(root, hipStreamCaptureModeGlobal));
      enqueue();
      HIP(hipStreamEndCapture(root, &graph));
      HIP(hipGraphInstantiate(&exec, graph, nullptr, nullptr, 0));
      size_t nodes = 0;
      HIP(hipGraphGetNodes(graph, nullptr, &nodes));
      fprintf(stderr, "GRAPH nodes=%zu\n", nodes);
    }
  }
  void run() {
    if (captured)
      HIP(hipGraphLaunch(exec, root));
    else
      enqueue();
  }
  ~Executable() {
    if (exec) HIP(hipGraphExecDestroy(exec));
    if (graph) HIP(hipGraphDestroy(graph));
  }
};
struct Timing {
  double gpu, host, submit;
};
inline Timing time_once(Executable& x) {
  Event begin(true), end(true);
  HIP(hipDeviceSynchronize());
  auto a = std::chrono::steady_clock::now();
  begin.record(x.root);
  x.run();
  end.record(x.root);
  auto b = std::chrono::steady_clock::now();
  HIP(hipEventSynchronize(end));
  auto c = std::chrono::steady_clock::now();
  float ms;
  HIP(hipEventElapsedTime(&ms, begin, end));
  return {ms * 1000.0, std::chrono::duration<double, std::micro>(c - a).count(),
          std::chrono::duration<double, std::micro>(b - a).count()};
}
inline void emit(const std::string& bench, const std::string& config, const std::string& schedule,
                 const std::string& phase, bool capture, int trial, const Timing& t, double err,
                 size_t bytes) {
  require(std::isfinite(t.gpu) && t.gpu > 0, "positive finite GPU time");
  printf("%s,%s,%s,%s,%s,%d,%.6f,%.6f,%.6f,%.9g,%zu,1\n", bench.c_str(), config.c_str(),
         schedule.c_str(), phase.c_str(), capture ? "graph" : "eager", trial, t.gpu, t.host,
         t.submit, err, bytes);
  fflush(stdout);
}
inline void measure(Context& c, const std::string& bench, const std::string& config,
                    const std::string& schedule, const std::string& phase, bool capture,
                    std::function<void()> fn, std::function<void()> prepare = {},
                    std::function<double()> check = {}, size_t bytes = 0) {
  if (prepare) prepare();
  Executable x(fn, c.s[0], capture);
  for (int t = -4; t < c.trials; ++t) {
    if (prepare) prepare();
    auto timing = time_once(x);
    double err = check ? check() : 0;
    require(std::isfinite(err), "finite correctness error");
    if (t >= 0) emit(bench, config, schedule, phase, capture, t, timing, err, bytes);
  }
}
__host__ __device__ inline uint32_t mix(uint32_t v) {
  v ^= v >> 16;
  v *= 0x7feb352dU;
  v ^= v >> 15;
  v *= 0x846ca68bU;
  return v ^ (v >> 16);
}
__host__ __device__ inline float value(uint32_t i) {
  return (int(mix(i) & 255) - 128) * (1.0f / 512);
}
inline float max_error(const float* a, const std::vector<float>& b, double tol) {
  double e = 0;
  for (size_t i = 0; i < b.size(); ++i) {
    require(std::isfinite(a[i]), "finite output");
    e = std::max(e, std::abs(double(a[i]) - b[i]));
  }
  require(e <= tol, "independent reference mismatch");
  return e;
}
inline std::vector<float> cached_reference(const std::string& key, size_t n,
                                           std::function<std::vector<float>()> generate) {
  const char* dir = getenv("LLM_REFERENCE_DIR");
  require(dir, "reference directory required");
  std::string path = std::string(dir) + "/" + key + ".bin";
  std::vector<float> v(n);
  std::ifstream in(path, std::ios::binary);
  if (in) {
    in.read(reinterpret_cast<char*>(v.data()), v.size() * 4);
    require(bool(in) && in.peek() == EOF, "reference file length");
    return v;
  }
  v = generate();
  require(v.size() == n, "reference size");
  std::ofstream out(path, std::ios::binary);
  out.write(reinterpret_cast<const char*>(v.data()), v.size() * 4);
  require(bool(out), "write reference");
  return v;
}
__host__ __device__ inline uint16_t bf16(float f) {
  union {
    float f;
    uint32_t u;
  } v;
  v.f = f;
  v.u += 0x7fff + ((v.u >> 16) & 1);
  return uint16_t(v.u >> 16);
}
__host__ __device__ inline float from_bf16(uint16_t h) {
  union {
    float f;
    uint32_t u;
  } v;
  v.u = uint32_t(h) << 16;
  return v.f;
}
