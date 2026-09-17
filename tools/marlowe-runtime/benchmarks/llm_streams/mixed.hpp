#pragma once
#include "experts.hpp"
#include "kv.hpp"
constexpr int SCAN_CHUNK = 256;
// The value-reduction part of decode attention with uniform softmax weights.
// Each input record is read once; no dot-product/exp loop disguises bandwidth work.
__global__ void value_scan_partial(const uint16_t* kv, float* partial, int tokens) {
  int chunks = tokens / SCAN_CHUNK, r = blockIdx.x / chunks, chunk = blockIdx.x % chunks,
      lane = threadIdx.x % 64, wave = threadIdx.x / 64;
  float acc[8] = {};
  for (int t = chunk * SCAN_CHUNK + wave; t < (chunk + 1) * SCAN_CHUNK; t += 4) {
    const auto row = kv + (size_t(r) * tokens + t) * KDIM;
    for (int x = 0; x < 8; ++x) acc[x] += from_bf16(row[lane + 64 * x]);
  }
  __shared__ float s[4][512];
  for (int x = 0; x < 8; ++x) s[wave][lane + 64 * x] = acc[x];
  __syncthreads();
  if (wave == 0)
    for (int x = 0; x < 8; ++x) {
      float sum = 0;
      for (int w = 0; w < 4; ++w) sum += s[w][lane + 64 * x];
      partial[size_t(blockIdx.x) * 512 + lane + 64 * x] = sum;
    }
}
__global__ void value_scan_finish(const float* partial, float* out, int tokens) {
  int r = blockIdx.x, d = threadIdx.x, chunks = tokens / SCAN_CHUNK;
  float sum = 0;
  for (int c = 0; c < chunks; ++c) sum += partial[(size_t(r) * chunks + c) * 512 + d];
  out[r * 512 + d] = sum / tokens;
}
struct Scan {
  Context& c;
  int requests = 8, tokens = 65536;
  uint32_t base;
  Device<unsigned char> kv;
  Device<float> partial, output;
  Scan(Context& context, uint32_t b)
      : c(context),
        base(b),
        kv(size_t(requests) * tokens * 1152),
        partial(size_t(requests) * tokens / SCAN_CHUNK * 512),
        output(size_t(requests) * 512) {
    init_records<<<(size_t(requests) * tokens * KDIM + 255) / 256, 256, 0, c.s[0]>>>(
        kv, requests * tokens, 0, base);
    HIP(hipDeviceSynchronize());
  }
  void run(hipStream_t stream) {
    value_scan_partial<<<requests * tokens / SCAN_CHUNK, 256, 0, stream>>>(
        reinterpret_cast<uint16_t*>(kv.p), partial, tokens);
    value_scan_finish<<<requests, 512, 0, stream>>>(partial, output, tokens);
  }
  std::vector<float> reference() {
    std::vector<float> result(output.n);
    for (int r = 0; r < requests; ++r) {
      std::array<double, 512> sum{};
      for (int t = 0; t < tokens; ++t)
        for (int d = 0; d < 512; ++d) sum[d] += kv_value(base + r * tokens + t, d);
      for (int d = 0; d < 512; ++d) result[r * 512 + d] = float(sum[d] / tokens);
    }
    return result;
  }
  size_t read_bytes() { return size_t(requests) * tokens * LATENT * 2; }
};
inline void benchmark_mixed(Context& c) {
  Routing r{512, {512, 0, 0, 0}, {0, 0, 0, 0}};
  Experts expert(c, r);
  Scan first(c, 700000), second(c, 1700000);
  auto er = cached_reference("mixed-expert", expert.merged.n, [&]() { return expert.reference(); });
  auto ar = cached_reference("mixed-scan0", first.output.n, [&]() { return first.reference(); });
  auto br = cached_reference("mixed-scan1", second.output.n, [&]() { return second.reference(); });
  std::vector<float> eo(er.size()), ao(ar.size()), bo(br.size());
  auto compute = [&]() {
    expert.expert(0, c.s[0]);
    expert.merge();
  };
  auto check = [&](bool memory) {
    HIP(hipMemcpy(ao.data(), first.output, first.output.bytes(), hipMemcpyDeviceToHost));
    double e = max_error(ao.data(), ar, 1e-6);
    if (memory) {
      HIP(hipMemcpy(bo.data(), second.output, second.output.bytes(), hipMemcpyDeviceToHost));
      e = std::max(e, double(max_error(bo.data(), br, 1e-6)));
    } else {
      HIP(hipMemcpy(eo.data(), expert.merged, expert.merged.bytes(), hipMemcpyDeviceToHost));
      e = std::max(e, double(max_error(eo.data(), er, 0.002)));
    }
    return e;
  };
  for (bool capture : {false, true}) {
    measure(c, "mixed", "matrix-kv", "isolated", "compute", capture, compute);
    measure(
        c, "mixed", "matrix-kv", "isolated", "scan0", capture, [&]() { first.run(c.s[0]); }, {}, {},
        first.read_bytes());
    measure(
        c, "mixed", "kv-kv", "isolated", "scan0", capture, [&]() { first.run(c.s[0]); }, {}, {},
        first.read_bytes());
    measure(
        c, "mixed", "kv-kv", "isolated", "scan1", capture, [&]() { second.run(c.s[0]); }, {}, {},
        second.read_bytes());
    for (bool memory : {false, true}) {
      Event fork, done;
      auto work0 = [&]() {
        if (memory)
          first.run(c.s[0]);
        else
          compute();
      };
      auto work1 = [&](hipStream_t s) {
        if (memory)
          second.run(s);
        else
          first.run(s);
      };
      Executable serial(
          [&]() {
            work0();
            work1(c.s[0]);
          },
          c.s[0], capture);
      Executable parallel(
          [&]() {
            fork.record(c.s[0]);
            fork.wait(c.s[1]);
            work1(c.s[1]);
            done.record(c.s[1]);
            work0();
            done.wait(c.s[0]);
          },
          c.s[0], capture);
      for (int t = -4; t < c.trials; ++t)
        for (int order = 0; order < 2; ++order) {
          int s = (order + t + 4) % 2;
          HIP(hipMemsetAsync(first.output, 0xff, first.output.bytes(), c.s[0]));
          HIP(hipMemsetAsync(second.output, 0xff, second.output.bytes(), c.s[0]));
          HIP(hipMemsetAsync(expert.merged, 0xff, expert.merged.bytes(), c.s[0]));
          HIP(hipStreamSynchronize(c.s[0]));
          auto tm = time_once(s ? parallel : serial);
          double error = check(memory);
          if (t >= 0)
            emit("mixed", memory ? "kv-kv" : "matrix-kv", s ? "parallel" : "serial", "total",
                 capture, t, tm, error, first.read_bytes() * (memory ? 2 : 1));
        }
    }
  }
}
