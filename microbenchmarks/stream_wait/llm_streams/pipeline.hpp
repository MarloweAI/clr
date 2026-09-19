#pragma once
#include "kv.hpp"
// Back up a newly produced latent+rope record for each request. Each later host
// check reads every element only after the final D2H event completed.
__global__ void pack_new_kv(const float* query, uint16_t* backup, int requests) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < requests * KDIM)
    backup[i] = uint16_t(__float_as_uint(query[(i / KDIM) * 32 * KDIM + i % KDIM]) >> 16);
}
__global__ void copy_bytes_kernel(const unsigned char* src, unsigned char* dst, size_t words) {
  size_t i = size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  for (; i < words; i += size_t(gridDim.x) * blockDim.x)
    reinterpret_cast<uint64_t*>(dst)[i] = reinterpret_cast<const uint64_t*>(src)[i];
}
inline void benchmark_pipeline(Context& c) {
  struct Shape {
    int h, layers, miss;
  };
  for (auto sh : std::vector<Shape>{{32, 8, 32}, {32, 32, 128}, {128, 8, 128}}) {
    int h = sh.h, L = sh.layers, miss = sh.miss, hit = 512, rb = 1152, pool = 512,
        requests = h / 32;
    std::string config =
        "h" + std::to_string(h) + "-l" + std::to_string(L) + "-miss" + std::to_string(miss);
    Pinned host(size_t(L) * pool * rb), backup(size_t(L) * requests * rb);
    for (int l = 0; l < L; ++l)
      for (int i = 0; i < pool; ++i)
        host_record(host.host + (size_t(l) * pool + i) * rb, l * pool + i, 0);
    std::vector<int> index(miss);
    for (int i = 0; i < miss; ++i) index[i] = (i * 17 + 7) % pool;
    Device<int> indices(miss);
    HIP(hipMemcpy(indices, index.data(), indices.bytes(), hipMemcpyHostToDevice));
    Device<unsigned char> resident(size_t(hit) * rb), buffer0(size_t(miss) * rb),
        buffer1(size_t(miss) * rb);
    unsigned char* buffers[2] = {buffer0.p, buffer1.p};
    Device<float> q(size_t(h) * KDIM), output(size_t(h) * LATENT);
    Device<uint16_t> newkv(size_t(L) * requests * KDIM);
    Device<Partial> a(h), b(h);
    init_records<<<(size_t(hit) * KDIM + 255) / 256, 256, 0, c.s[0]>>>(resident, hit, 0, 100000);
    HIP(hipDeviceSynchronize());
    auto q0 = query_values(h), qref = q0;
    std::vector<uint16_t> backup_ref(size_t(L) * requests * KDIM);
    for (int l = 0; l < L; ++l) {
      std::vector<uint32_t> ids;
      for (int i = 0; i < hit; ++i) ids.push_back(100000 + i);
      for (int i : index) ids.push_back(l * pool + i);
      auto o = attention_reference(qref, h, ids);
      for (int head = 0; head < h; ++head)
        for (int d = 0; d < LATENT; ++d)
          qref[head * KDIM + d] = std::fma(0.125f, o[head * LATENT + d], qref[head * KDIM + d]);
      for (int i = 0; i < requests * KDIM; ++i) {
        uint32_t bits;
        std::memcpy(&bits, &qref[(i / KDIM) * 32 * KDIM + i % KDIM], 4);
        backup_ref[size_t(l) * requests * KDIM + i] = uint16_t(bits >> 16);
      }
    }
    std::vector<float> actual(qref.size());
    auto prepare = [&]() {
      HIP(hipMemcpyAsync(q, q0.data(), q.bytes(), hipMemcpyHostToDevice, c.s[0]));
      HIP(hipMemsetAsync(buffer0, 0xff, buffer0.bytes(), c.s[0]));
      HIP(hipMemsetAsync(buffer1, 0xff, buffer1.bytes(), c.s[0]));
      std::memset(backup.host, 0xff, backup.n);
      HIP(hipStreamSynchronize(c.s[0]));
    };
    auto check = [&]() {
      HIP(hipMemcpy(actual.data(), q, q.bytes(), hipMemcpyDeviceToHost));
      double e = max_error(actual.data(), qref, 1e-4);
      auto out = reinterpret_cast<uint16_t*>(backup.host);
      for (size_t i = 0; i < backup_ref.size(); ++i) {
        uint32_t a32 = uint32_t(out[i]) << 16, b32 = uint32_t(backup_ref[i]) << 16;
        float a, b;
        std::memcpy(&a, &a32, 4);
        std::memcpy(&b, &b32, 4);
        require(std::isfinite(a) && std::abs(a - b) <= 0.002, "per-layer D2H backup reference");
      }
      return e;
    };
    auto copy = [&](int l, hipStream_t s) {
      gather_records<<<16, 1024, 0, s>>>(host.device + size_t(l) * pool * rb, buffers[l % 2],
                                         indices, miss, rb);
    };
    auto compute = [&](int l) {
      attention<<<h, 256, 0, c.s[0]>>>(q, resident, a, h, hit, 0);
      attention<<<h, 256, 0, c.s[0]>>>(q, buffers[l % 2], b, h, miss, 0);
      merge_parts<<<h, LATENT, 0, c.s[0]>>>(a, b, output, q, h, true);
      pack_new_kv<<<(requests * KDIM + 255) / 256, 256, 0, c.s[0]>>>(
          q, newkv.p + size_t(l) * requests * KDIM, requests);
    };
    auto writeback = [&](int l, hipStream_t s) {
      HIP(hipMemcpyAsync(backup.host + size_t(l) * requests * rb,
                         newkv.p + size_t(l) * requests * KDIM, size_t(requests) * rb,
                         hipMemcpyDeviceToHost, s));
    };
    for (bool capture : {false, true}) {
      prepare();
      copy(0, c.s[0]);
      compute(0);
      HIP(hipDeviceSynchronize());
      measure(
          c, "pipeline", config, "isolated", "h2d", capture, [&]() { copy(0, c.s[0]); }, {}, {},
          size_t(miss) * rb);
      measure(
          c, "pipeline", config, "isolated", "compute", capture, [&]() { compute(0); },
          [&]() { HIP(hipMemcpy(q, q0.data(), q.bytes(), hipMemcpyHostToDevice)); });
      measure(
          c, "pipeline", config, "isolated", "d2h", capture, [&]() { writeback(0, c.s[0]); }, {},
          {}, size_t(requests) * rb);
      std::array<Event, 32> ready, consumed, produced, written;
      Event fork;
      auto enqueue = [&](int schedule) {
        if (schedule == 0) {
          for (int l = 0; l < L; ++l) {
            copy(l, c.s[0]);
            compute(l);
            writeback(l, c.s[0]);
          }
          return;
        }
        fork.record(c.s[0]);
        fork.wait(c.s[1]);
        if (schedule == 2) fork.wait(c.s[2]);
        copy(0, c.s[1]);
        ready[0].record(c.s[1]);
        for (int l = 0; l < L; ++l) {
          // Plan for l+1 is already known; reuse a buffer only after its reader.
          if (l + 1 < L) {
            if (l >= 1) consumed[l - 1].wait(c.s[1]);
            copy(l + 1, c.s[1]);
            ready[l + 1].record(c.s[1]);
          }
          ready[l].wait(c.s[0]);
          compute(l);
          consumed[l].record(c.s[0]);
          produced[l].record(c.s[0]);
          hipStream_t out = schedule == 2 ? c.s[2] : c.s[1];
          produced[l].wait(out);
          writeback(l, out);
          written[l].record(out);
        }
        written[L - 1].wait(c.s[0]);
      };
      prepare();
      Executable serial([&]() { enqueue(0); }, c.s[0], capture);
      prepare();
      Executable two([&]() { enqueue(1); }, c.s[0], capture);
      prepare();
      Executable three([&]() { enqueue(2); }, c.s[0], capture);
      Executable* paths[] = {&serial, &two, &three};
      const char* names[] = {"serial", "two_streams", "three_streams"};
      for (int t = -4; t < c.trials; ++t)
        for (int order = 0; order < 3; ++order) {
          int s = (order + t + 6) % 3;
          prepare();
          auto tm = time_once(*paths[s]);
          double e = check();
          if (t >= 0)
            emit("pipeline", config, names[s], "total", capture, t, tm, e,
                 size_t(L) * (miss + requests) * rb);
        }
    }
  }
}
