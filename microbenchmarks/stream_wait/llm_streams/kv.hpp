#pragma once
#include "common.hpp"
constexpr int LATENT = 512, ROPE = 64, KDIM = LATENT + ROPE, LANES = 64, WAVES = 4;
__host__ __device__ inline int record_bytes(int layout) { return layout == 0 ? 1152 : 584; }
__host__ __device__ inline float kv_value(uint32_t id, int d) {
  return value(id * 7919u + uint32_t(d) * 13u);
}
__device__ inline float load_kv(const unsigned char* p, int d, int layout) {
  if (layout == 0) return __uint_as_float(uint32_t(reinterpret_cast<const uint16_t*>(p)[d]) << 16);
  return float(reinterpret_cast<const int8_t*>(p)[d]) *
         reinterpret_cast<const float*>(p + 576)[d < 512 ? 0 : 1];
}
inline void host_record(unsigned char* p, uint32_t id, int layout) {
  for (int d = 0; d < KDIM; ++d) {
    float f = kv_value(id, d);
    if (layout == 0) {
      uint32_t bits;
      std::memcpy(&bits, &f, 4);
      reinterpret_cast<uint16_t*>(p)[d] = uint16_t(bits >> 16);
    } else
      reinterpret_cast<int8_t*>(p)[d] = int8_t(std::lround(f * 512));
  }
  if (layout) {
    reinterpret_cast<float*>(p + 576)[0] = 1.0f / 512;
    reinterpret_cast<float*>(p + 576)[1] = 1.0f / 512;
  }
}
__global__ void init_records(unsigned char* p, int count, int layout, uint32_t base) {
  size_t i = size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i >= size_t(count) * KDIM) return;
  int t = i / KDIM, d = i % KDIM;
  auto row = p + size_t(t) * record_bytes(layout);
  float f = kv_value(base + t, d);
  if (layout == 0)
    reinterpret_cast<uint16_t*>(row)[d] = uint16_t(__float_as_uint(f) >> 16);
  else {
    reinterpret_cast<int8_t*>(row)[d] = int8_t(f * 512);
    if (d < 2) reinterpret_cast<float*>(row + 576)[d] = 1.0f / 512;
  }
}
__global__ void gather_records(const unsigned char* host, unsigned char* dst, const int* indices,
                               int count, int stride) {
  int wave = (blockIdx.x * blockDim.x + threadIdx.x) / 64, lane = threadIdx.x % 64,
      step = gridDim.x * (blockDim.x / 64);
  for (int j = wave; j < count; j += step) {
    auto source = host + size_t(indices[j]) * stride;
    auto target = dst + size_t(j) * stride;
    if (stride >= 1024 && stride % 16 == 0) {
      using V = __attribute__((__vector_size__(16))) uint32_t;
      auto src = reinterpret_cast<const V*>(source);
      auto out = reinterpret_cast<V*>(target);
      for (int w = lane; w < stride / 16; w += 64) out[w] = __builtin_nontemporal_load(src + w);
    } else {
      auto src = reinterpret_cast<const uint64_t*>(source);
      auto out = reinterpret_cast<uint64_t*>(target);
      for (int w = lane; w < stride / 8; w += 64) out[w] = src[w];
    }
  }
}
struct Partial {
  float m, l, v[LATENT];
};
__global__ void attention(const float* q, const unsigned char* kv, Partial* out, int heads,
                          int tokens, int layout) {
  int h = blockIdx.x, lane = threadIdx.x % 64, wave = threadIdx.x / 64;
  float qv[9], acc[8] = {};
  for (int x = 0; x < 9; ++x) qv[x] = q[h * KDIM + lane + 64 * x];
  float m = -INFINITY, den = 0;
  for (int t = wave; t < tokens; t += WAVES) {
    const auto row = kv + size_t(t) * record_bytes(layout);
    float dot = 0, vs[8];
    for (int x = 0; x < 9; ++x) {
      float k = load_kv(row, lane + 64 * x, layout);
      dot = fmaf(qv[x], k, dot);
      if (x < 8) vs[x] = k;
    }
    for (int d = 32; d; d /= 2) dot += __shfl_down(dot, d, 64);
    dot = __shfl(dot, 0, 64) * (1.0f / 24);
    float nm = fmaxf(m, dot), a = expf(m - nm), b = expf(dot - nm);
    den = den * a + b;
    for (int x = 0; x < 8; ++x) acc[x] = acc[x] * a + b * vs[x];
    m = nm;
  }
  __shared__ float sm[4], sl[4], sv[4][512];
  if (lane == 0) {
    sm[wave] = m;
    sl[wave] = den;
  }
  for (int x = 0; x < 8; ++x) sv[wave][lane + 64 * x] = acc[x];
  __syncthreads();
  if (wave == 0) {
    float mm = -INFINITY, ll = 0;
    for (int w = 0; w < 4; ++w) mm = fmaxf(mm, sm[w]);
    float z[8] = {};
    for (int w = 0; w < 4; ++w) {
      float a = sl[w] > 0 ? expf(sm[w] - mm) : 0;
      ll += sl[w] * a;
      for (int x = 0; x < 8; ++x) z[x] += sv[w][lane + 64 * x] * a;
    }
    for (int x = 0; x < 8; ++x) out[h].v[lane + 64 * x] = z[x];
    if (lane == 0) {
      out[h].m = mm;
      out[h].l = ll;
    }
  }
}
__global__ void merge_parts(const Partial* a, const Partial* b, float* output, float* query,
                            int heads, bool update) {
  int h = blockIdx.x, d = threadIdx.x;
  float m = fmaxf(a[h].m, b[h].m), sa = expf(a[h].m - m), sb = expf(b[h].m - m);
  float z = (sa * a[h].v[d] + sb * b[h].v[d]) / (sa * a[h].l + sb * b[h].l);
  output[h * LATENT + d] = z;
  if (update) query[h * KDIM + d] = fmaf(0.125f, z, query[h * KDIM + d]);
}
__global__ void normalize_part(const Partial* a, float* output, float* query, int heads,
                               bool update) {
  int h = blockIdx.x, d = threadIdx.x;
  float z = a[h].v[d] / a[h].l;
  output[h * LATENT + d] = z;
  if (update) query[h * KDIM + d] = fmaf(0.125f, z, query[h * KDIM + d]);
}
inline std::vector<float> query_values(int heads) {
  std::vector<float> q(size_t(heads) * KDIM);
  for (size_t i = 0; i < q.size(); ++i) q[i] = value(uint32_t(i) + 123);
  return q;
}
inline std::vector<float> attention_reference(const std::vector<float>& q, int heads,
                                              const std::vector<uint32_t>& ids) {
  std::vector<float> out(size_t(heads) * LATENT);
  std::vector<double> score(ids.size());
  for (int h = 0; h < heads; ++h) {
    double m = -INFINITY;
    for (size_t t = 0; t < ids.size(); ++t) {
      double dot = 0;
      for (int d = 0; d < KDIM; ++d) dot += double(q[h * KDIM + d]) * kv_value(ids[t], d);
      score[t] = dot / 24;
      m = std::max(m, score[t]);
    }
    double den = 0;
    std::array<double, LATENT> acc{};
    for (size_t t = 0; t < ids.size(); ++t) {
      double w = std::exp(score[t] - m);
      den += w;
      for (int d = 0; d < LATENT; ++d) acc[d] += w * kv_value(ids[t], d);
    }
    for (int d = 0; d < LATENT; ++d) out[h * LATENT + d] = float(acc[d] / den);
  }
  return out;
}
