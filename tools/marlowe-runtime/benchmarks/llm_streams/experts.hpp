#pragma once
#include "common.hpp"
struct Routing {
  int batch, counts[4], starts[4];
};
__host__ __device__ inline float wa(int i, int e, int layer) {
  return ((int(mix(i + e * 17 + layer * 613) & 3) - 1)) * (1.0f / 32);
}
__host__ __device__ inline float wb(int i, int e, int layer) {
  return ((int(mix(i + e * 191 + layer * 997) & 3) - 1)) * (1.0f / 16);
}
__global__ void init_weights(uint16_t* w1, uint16_t* w2, int K, int N) {
  size_t i = size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i >= size_t(4) * K * N) return;
  int e = i / (size_t(K) * N), j = i % (size_t(K) * N);
  w1[i] = bf16(wa(j / N, e, 0) * wb(j % N, e, 0));
  w2[i] = bf16(wa(j / K, e, 1) * wb(j % K, e, 1));
}
__global__ void init_inputs(uint16_t* x, int K, int stride, Routing r) {
  size_t i = size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i >= size_t(4) * stride * K) return;
  int e = i / (size_t(stride) * K), j = i % (size_t(stride) * K), t = j / K, d = j % K;
  x[i] = bf16(value(uint32_t(r.starts[e] + t) * K + d + 315));
}
__global__ void silu(uint16_t* p, size_t n) {
  size_t i = size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i < n) {
    float x = from_bf16(p[i]);
    p[i] = bf16(x / (1 + expf(-x)));
  }
}
__global__ void route_merge(const uint16_t* y, float* out, int K, int stride, Routing r) {
  size_t i = size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i >= size_t(r.batch) * K) return;
  int t = i / K, d = i % K;
  float sum = 0;
  for (int e = 0; e < 4; ++e)
    if (t >= r.starts[e] && t < r.starts[e] + r.counts[e])
      sum += 0.5f * from_bf16(y[(size_t(e) * stride + t - r.starts[e]) * K + d]);
  out[i] = sum;
}
struct Experts {
  Context& ctx;
  Routing routing;
  int K = 4096, N = 4096, stride;
  Device<uint16_t> w1, w2, x, h, y;
  Device<float> merged;
  rocblas_handle handles[4]{};
  float alpha = 1, beta = 0;
  Experts(Context& c, Routing r)
      : ctx(c),
        routing(r),
        stride(*std::max_element(r.counts, r.counts + 4)),
        w1(size_t(4) * K * N),
        w2(size_t(4) * K * N),
        x(size_t(4) * stride * K),
        h(size_t(4) * stride * N),
        y(size_t(4) * stride * K),
        merged(size_t(r.batch) * K) {
    init_weights<<<(w1.n + 255) / 256, 256, 0, c.s[0]>>>(w1, w2, K, N);
    init_inputs<<<(x.n + 255) / 256, 256, 0, c.s[0]>>>(x, K, stride, r);
    HIP(hipDeviceSynchronize());
    for (auto& handle : handles) {
      BLAS(rocblas_create_handle(&handle));
      BLAS(rocblas_set_pointer_mode(handle, rocblas_pointer_mode_host));
    }
  }
  ~Experts() {
    HIP(hipDeviceSynchronize());
    for (auto h : handles) BLAS(rocblas_destroy_handle(h));
  }
  void expert(int e, hipStream_t stream) {
    int M = routing.counts[e];
    require(M > 0, "positive expert batch");
    auto handle = handles[e];
    BLAS(rocblas_set_stream(handle, stream));
    auto H = h.p + size_t(e) * stride * N;
    auto Y = y.p + size_t(e) * stride * K;
    BLAS(rocblas_gemm_ex(handle, rocblas_operation_none, rocblas_operation_none, N, M, K, &alpha,
                         w1.p + size_t(e) * N * K, rocblas_datatype_bf16_r, N,
                         x.p + size_t(e) * stride * K, rocblas_datatype_bf16_r, K, &beta, H,
                         rocblas_datatype_bf16_r, N, H, rocblas_datatype_bf16_r, N,
                         rocblas_datatype_f32_r, rocblas_gemm_algo_standard, 0, 0));
    silu<<<(size_t(M) * N + 255) / 256, 256, 0, stream>>>(H, size_t(M) * N);
    BLAS(rocblas_gemm_ex(handle, rocblas_operation_none, rocblas_operation_none, K, M, N, &alpha,
                         w2.p + size_t(e) * N * K, rocblas_datatype_bf16_r, K, H,
                         rocblas_datatype_bf16_r, N, &beta, Y, rocblas_datatype_bf16_r, K, Y,
                         rocblas_datatype_bf16_r, K, rocblas_datatype_f32_r,
                         rocblas_gemm_algo_standard, 0, 0));
  }
  void batch() {
    int M = routing.counts[0];
    for (int e = 1; e < 4; ++e) require(routing.counts[e] == M, "balanced batch required");
    auto handle = handles[0];
    BLAS(rocblas_set_stream(handle, ctx.s[0]));
    BLAS(rocblas_gemm_strided_batched_ex(
        handle, rocblas_operation_none, rocblas_operation_none, N, M, K, &alpha, w1,
        rocblas_datatype_bf16_r, N, size_t(N) * K, x, rocblas_datatype_bf16_r, K,
        size_t(stride) * K, &beta, h, rocblas_datatype_bf16_r, N, size_t(stride) * N, h,
        rocblas_datatype_bf16_r, N, size_t(stride) * N, 4, rocblas_datatype_f32_r,
        rocblas_gemm_algo_standard, 0, 0));
    silu<<<(size_t(4) * M * N + 255) / 256, 256, 0, ctx.s[0]>>>(h, size_t(4) * M * N);
    BLAS(rocblas_gemm_strided_batched_ex(
        handle, rocblas_operation_none, rocblas_operation_none, K, M, N, &alpha, w2,
        rocblas_datatype_bf16_r, K, size_t(N) * K, h, rocblas_datatype_bf16_r, N,
        size_t(stride) * N, &beta, y, rocblas_datatype_bf16_r, K, size_t(stride) * K, y,
        rocblas_datatype_bf16_r, K, size_t(stride) * K, 4, rocblas_datatype_f32_r,
        rocblas_gemm_algo_standard, 0, 0));
  }
  void merge() {
    route_merge<<<(merged.n + 255) / 256, 256, 0, ctx.s[0]>>>(y, merged, K, stride, routing);
  }
  std::vector<float> reference() {
    std::vector<float> result(merged.n, 0);
    for (int e = 0; e < 4; ++e)
      for (int t = 0; t < routing.counts[e]; ++t) {
        int original = routing.starts[e] + t;
        double z = 0;
        for (int k = 0; k < K; ++k)
          z += double(value(uint32_t(original) * K + k + 315)) * wa(k, e, 0);
        double sum = 0;
        for (int n = 0; n < N; ++n) {
          float hidden = from_bf16(bf16(float(z * wb(n, e, 0))));
          float activated = from_bf16(bf16(hidden / (1 + std::exp(-hidden))));
          sum += double(activated) * wa(n, e, 1);
        }
        for (int k = 0; k < K; ++k)
          result[size_t(original) * K + k] += 0.5f * from_bf16(bf16(float(sum * wb(k, e, 1))));
      }
    return result;
  }
};
inline void benchmark_experts(Context& c) {
  std::vector<Routing> routings = {{16, {8, 8, 8, 8}, {0, 8, 0, 8}},
                                   {64, {32, 32, 32, 32}, {0, 32, 0, 32}},
                                   {64, {64, 48, 8, 8}, {0, 0, 48, 56}}};
  for (auto r : routings) {
    bool balanced = r.counts[0] == r.counts[1];
    std::string config = "b" + std::to_string(r.batch) + (balanced ? "-balanced" : "-skewed");
    Experts e(c, r);
    auto ref = cached_reference("experts-" + config, e.merged.n, [&]() { return e.reference(); });
    std::vector<float> actual(ref.size());
    auto check = [&]() {
      HIP(hipMemcpy(actual.data(), e.merged, e.merged.bytes(), hipMemcpyDeviceToHost));
      return max_error(actual.data(), ref, 0.002);
    };
    for (bool capture : {false, true}) {
      for (int i = 0; i < 4; ++i)
        measure(c, "experts", config, "isolated", "expert" + std::to_string(i), capture,
                [&, i]() { e.expert(i, c.s[0]); });
      e.merge();
      HIP(hipDeviceSynchronize());
      measure(c, "experts", config, "isolated", "merge", capture, [&]() { e.merge(); });
      Event fork;
      std::array<Event, 4> done;
      auto enqueue = [&](int streams) {
        if (streams == 0) {
          e.batch();
          e.merge();
          return;
        }
        if (streams == 1) {
          for (int i = 0; i < 4; ++i) e.expert(i, c.s[0]);
          e.merge();
          return;
        }
        fork.record(c.s[0]);
        for (int s = 1; s < streams; ++s) fork.wait(c.s[s]);
        for (int i = 0; i < 4; ++i) e.expert(i, c.s[i % streams]);
        for (int s = 1; s < streams; ++s) done[s].record(c.s[s]);
        for (int s = 1; s < streams; ++s) done[s].wait(c.s[0]);
        e.merge();
      };
      std::vector<std::unique_ptr<Executable>> paths;
      std::vector<int> modes = {1, 2, 4};
      if (balanced) modes.push_back(0);
      for (int s : modes)
        paths.emplace_back(new Executable([&, s]() { enqueue(s); }, c.s[0], capture));
      for (int t = -4; t < c.trials; ++t)
        for (size_t order = 0; order < modes.size(); ++order) {
          size_t i = (order + t + 4) % modes.size();
          HIP(hipMemsetAsync(e.y, 0xff, e.y.bytes(), c.s[0]));
          HIP(hipMemsetAsync(e.merged, 0xff, e.merged.bytes(), c.s[0]));
          HIP(hipStreamSynchronize(c.s[0]));
          auto tm = time_once(*paths[i]);
          double err = check();
          std::string name = modes[i] ? std::to_string(modes[i]) + "_streams" : "batched";
          if (t >= 0)
            emit("experts", config, name, "total", capture, t, tm, err, size_t(8) * e.K * e.N * 2);
        }
    }
  }
}
