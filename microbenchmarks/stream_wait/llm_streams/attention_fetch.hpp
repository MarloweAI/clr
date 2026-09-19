#pragma once
#include "kv.hpp"
inline void benchmark_attention_fetch(Context& c) {
  struct Shape {
    int h, miss, layout;
  };
  std::vector<Shape> shapes = {
      {32, 32, 0}, {32, 128, 0}, {32, 256, 0}, {128, 128, 0}, {32, 128, 1}};
  for (auto sh : shapes) {
    int h = sh.h, miss = sh.miss, total = 2048, hit = total - miss, rb = record_bytes(sh.layout),
        pool = 8192;
    std::string config =
        "h" + std::to_string(h) + "-miss" + std::to_string(miss) + "-r" + std::to_string(rb);
    Pinned host(size_t(pool) * rb);
    for (int i = 0; i < pool; ++i) host_record(host.host + size_t(i) * rb, i, sh.layout);
    std::vector<int> index(miss);
    std::vector<uint32_t> ids;
    for (int i = 0; i < hit; ++i) ids.push_back(65536 + i);
    for (int i = 0; i < miss; ++i) {
      index[i] = (i * 17 + 23) % pool;
      ids.push_back(index[i]);
    }
    Device<int> indices(miss);
    Device<unsigned char> resident(size_t(hit) * rb), restored(size_t(miss) * rb);
    Device<float> q(size_t(h) * KDIM), output(size_t(h) * LATENT);
    Device<Partial> a(h), b(h);
    auto qhost = query_values(h);
    HIP(hipMemcpy(q, qhost.data(), q.bytes(), hipMemcpyHostToDevice));
    HIP(hipMemcpy(indices, index.data(), indices.bytes(), hipMemcpyHostToDevice));
    init_records<<<(size_t(hit) * KDIM + 255) / 256, 256, 0, c.s[0]>>>(resident, hit, sh.layout,
                                                                       65536);
    HIP(hipDeviceSynchronize());
    auto reference = cached_reference("fetch-" + config, size_t(h) * LATENT,
                                      [&]() { return attention_reference(qhost, h, ids); });
    std::vector<float> actual(reference.size());
    auto check = [&]() {
      HIP(hipMemcpy(actual.data(), output, output.bytes(), hipMemcpyDeviceToHost));
      return max_error(actual.data(), reference, 3e-5);
    };
    for (bool capture : {false, true})
      for (const std::string path : {"gather", "memcpy"}) {
        auto copy = [&](hipStream_t stream) {
          if (path == "gather")
            gather_records<<<16, 1024, 0, stream>>>(host.device, restored, indices, miss, rb);
          else
            for (int i = 0; i < miss; ++i)
              HIP(hipMemcpyAsync(restored.p + size_t(i) * rb, host.host + size_t(index[i]) * rb, rb,
                                 hipMemcpyHostToDevice, stream));
        };
        auto resident_attn = [&](hipStream_t s) {
          attention<<<h, 256, 0, s>>>(q, resident, a, h, hit, sh.layout);
        };
        auto miss_attn = [&](hipStream_t s) {
          attention<<<h, 256, 0, s>>>(q, restored, b, h, miss, sh.layout);
        };
        auto merge = [&]() { merge_parts<<<h, LATENT, 0, c.s[0]>>>(a, b, output, q, h, false); };
        copy(c.s[0]);
        resident_attn(c.s[0]);
        miss_attn(c.s[0]);
        HIP(hipDeviceSynchronize());
        measure(
            c, "attention_fetch", config, path, "copy", capture, [&]() { copy(c.s[0]); }, {}, {},
            size_t(miss) * rb);
        measure(c, "attention_fetch", config, path, "resident", capture,
                [&]() { resident_attn(c.s[0]); });
        measure(c, "attention_fetch", config, path, "miss_attention", capture,
                [&]() { miss_attn(c.s[0]); });
        measure(c, "attention_fetch", config, path, "merge", capture, merge);
        Event fork, join;
        std::array<std::function<void()>, 2> schedules = {[&]() {
                                                            copy(c.s[0]);
                                                            resident_attn(c.s[0]);
                                                            miss_attn(c.s[0]);
                                                            merge();
                                                          },
                                                          [&]() {
                                                            fork.record(c.s[0]);
                                                            fork.wait(c.s[1]);
                                                            copy(c.s[1]);
                                                            miss_attn(c.s[1]);
                                                            join.record(c.s[1]);
                                                            resident_attn(c.s[0]);
                                                            join.wait(c.s[0]);
                                                            merge();
                                                          }};
        // Alternate complete schedules every trial, with identical addresses and work.
        Executable serial(schedules[0], c.s[0], capture), parallel(schedules[1], c.s[0], capture);
        for (int t = -4; t < c.trials; ++t)
          for (int order = 0; order < 2; ++order) {
            int s = (order + t + 4) % 2;
            HIP(hipMemsetAsync(restored, 0xff, restored.bytes(), c.s[0]));
            HIP(hipMemsetAsync(output, 0xff, output.bytes(), c.s[0]));
            HIP(hipStreamSynchronize(c.s[0]));
            auto tm = time_once(s ? parallel : serial);
            double err = check();
            if (t >= 0)
              emit("attention_fetch", config, path + (s ? "-parallel" : "-serial"), "total",
                   capture, t, tm, err, size_t(miss) * rb);
          }
      }
  }
}
