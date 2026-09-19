#pragma once
#include "pipeline.hpp"
// GPU-produced shared plan. Deterministic integer state allows an independent
// CPU reference; this models data dependencies, not the cost of real top-k/LRU.
__global__ void grouped_plan(int* indices, const int* seed, int miss, int pool, int groups) {
  for (int i = threadIdx.x; i < miss; i += blockDim.x)
    indices[i] = (i * 17 + 7 + (*seed % groups) * 13) % pool;
}
__global__ void grouped_advance(int* seed) { ++*seed; }
__global__ void grouped_plan_delay(unsigned long long ticks) {
  auto start = wall_clock64();
  while (wall_clock64() - start < ticks) {}
}
// Merge unnormalized softmax summaries from disjoint resident-token ranges
// and the restored KV range. Every input token participates exactly once.
__global__ void grouped_merge_splits(const Partial* resident, const Partial* restored,
                                     float* output, float* query, int heads, int splits) {
  int h = blockIdx.x, d = threadIdx.x;
  float m = restored[h].m, den = restored[h].l, acc = restored[h].v[d];
  for (int part = 0; part < splits; ++part) {
    const Partial& x = resident[part * heads + h];
    float next = fmaxf(m, x.m), a = expf(m - next), b = expf(x.m - next);
    acc = a * acc + b * x.v[d];
    den = a * den + b * x.l;
    m = next;
  }
  float z = acc / den;
  output[h * LATENT + d] = z;
  query[h * KDIM + d] = fmaf(0.125f, z, query[h * KDIM + d]);
}
inline void benchmark_grouped_prefetch(Context& c) {
  struct Shape {
    int h, layers, miss;
  };
  const int heads = getenv("LLM_GROUP_HEADS") ? std::stoi(getenv("LLM_GROUP_HEADS")) : 32;
  require(heads == 32 || heads == 256 || heads == 512, "group heads must be 32, 256, or 512");
  const int splits = getenv("LLM_GROUP_SPLITS") ? std::stoi(getenv("LLM_GROUP_SPLITS")) : 1;
  require(splits == 1 || splits == 22 || splits == 38, "group splits must be 1, 22, or 38");
  const int depth = getenv("LLM_GROUP_DEPTH") ? std::stoi(getenv("LLM_GROUP_DEPTH")) : 1;
  require(depth == 1 || depth == 8, "group depth must be 1 or 8");
  const int plan_us = getenv("LLM_GROUP_PLAN_US") ? std::stoi(getenv("LLM_GROUP_PLAN_US")) : 0;
  require(plan_us >= 0 && plan_us <= 500, "plan delay must be 0..500 us");
  const bool main_backup = getenv("LLM_GROUP_MAIN_BACKUP") &&
                           std::string(getenv("LLM_GROUP_MAIN_BACKUP")) == "1";
  int clock_khz = 0;
  HIP(hipDeviceGetAttribute(&clock_khz, hipDeviceAttributeWallClockRate, 0));
  require(clock_khz > 0, "wall clock rate available");
  for (auto sh : std::vector<Shape>{{heads, 8, 32}, {heads, 32, 128}, {heads, 64, 128}}) {
    int h = sh.h, L = sh.layers, miss = sh.miss, hit = 512, rb = 1152, pool = 512,
        requests = h / 32;
    std::string config =
        "h" + std::to_string(h) + "-l" + std::to_string(L) + "-miss" + std::to_string(miss) + "-depth" + std::to_string(depth) + "-planus" + std::to_string(plan_us) +
        (main_backup ? "-backupmain" : "-backupside");
    if (splits != 1) config += "-splits" + std::to_string(splits);
    Pinned host(size_t(L) * pool * rb), backup(size_t(L) * requests * rb);
    for (int l = 0; l < L; ++l)
      for (int i = 0; i < pool; ++i)
        host_record(host.host + (size_t(l) * pool + i) * rb, l * pool + i, 0);
    constexpr int group_size = 4;
    Device<int> indices(miss), seed(1);
    Device<unsigned char> resident(size_t(hit) * rb), buffers(size_t(L) * miss * rb);
    Device<float> q(size_t(h) * KDIM), output(size_t(h) * LATENT);
    Device<uint16_t> newkv(size_t(L) * requests * KDIM);
    Device<Partial> a(size_t(h) * splits), b(h);
    init_records<<<(size_t(hit) * KDIM + 255) / 256, 256, 0, c.s[0]>>>(resident, hit, 0, 100000);
    HIP(hipDeviceSynchronize());
    auto q0 = query_values(h), qref = q0;
    std::vector<uint16_t> backup_ref(size_t(L) * requests * KDIM);
    for (int replay = 0; replay < depth; ++replay)
    for (int l = 0; l < L; ++l) {
      std::vector<uint32_t> ids;
      for (int i = 0; i < hit; ++i) ids.push_back(100000 + i);
      for (int i = 0; i < miss; ++i)
        ids.push_back(l * pool + (i * 17 + 7 + l / group_size * 13) % pool);
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
      HIP(hipMemsetAsync(buffers, 0xff, buffers.bytes(), c.s[0]));
      HIP(hipMemsetAsync(indices, 0xff, indices.bytes(), c.s[0]));
      HIP(hipMemsetAsync(seed, 0, seed.bytes(), c.s[0]));
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
    auto plan = [&]() {
      // Artificial critical-path duration control, not simulated planning work.
      if (plan_us) grouped_plan_delay<<<1, 1, 0, c.s[0]>>>(
          static_cast<unsigned long long>(clock_khz) * plan_us / 1000);
      grouped_plan<<<1, 256, 0, c.s[0]>>>(indices, seed, miss, pool, L / group_size);
      grouped_advance<<<1, 1, 0, c.s[0]>>>(seed);
    };
    auto copy = [&](int l, hipStream_t s) {
      gather_records<<<16, 1024, 0, s>>>(host.device + size_t(l) * pool * rb, buffers.p + size_t(l) * miss * rb,
                                         indices, miss, rb);
    };
    auto compute = [&](int l) {
      for (int part = 0; part < splits; ++part) {
        int begin = hit * part / splits, end = hit * (part + 1) / splits;
        attention<<<h, 256, 0, c.s[0]>>>(q, resident.p + size_t(begin) * rb,
                                         a.p + size_t(part) * h, h, end - begin, 0);
      }
      attention<<<h, 256, 0, c.s[0]>>>(q, buffers.p + size_t(l) * miss * rb, b, h, miss, 0);
      if (splits == 1)
        merge_parts<<<h, LATENT, 0, c.s[0]>>>(a, b, output, q, h, true);
      else
        grouped_merge_splits<<<h, LATENT, 0, c.s[0]>>>(a, b, output, q, h, splits);
      pack_new_kv<<<(requests * KDIM + 255) / 256, 256, 0, c.s[0]>>>(
          q, newkv.p + size_t(l) * requests * KDIM, requests);
    };
    auto writeback = [&](int l, hipStream_t s) {
      HIP(hipMemcpyAsync(backup.host + size_t(l) * requests * rb,
                         newkv.p + size_t(l) * requests * KDIM, size_t(requests) * rb,
                         hipMemcpyDeviceToHost, s));
    };
    for (bool capture : {false, true}) {
      std::array<Event, 64> ready, produced, written;
      std::array<Event, 64> fork;
      auto enqueue = [&](int schedule) {
        // All schedules keep backups on a separate stream, like retained HiSparse.
        // schedule 0 disables prefetch only; schedule 1 uses standard per-layer events.
        for (int l = 0; l < L; ++l) {
          if (l % group_size == 0) {
            plan();
            copy(l, c.s[0]);
            if (schedule == 1) {
              fork[l].record(c.s[0]);
              fork[l].wait(c.s[1]);
              for (int follower = l + 1; follower < std::min(l + group_size, L); ++follower) {
                copy(follower, c.s[1]);
                ready[follower].record(c.s[1]);
              }
            }
          } else if (schedule == 1) {
            ready[l].wait(c.s[0]);
          } else {
            copy(l, c.s[0]);
          }
          compute(l);
          if (main_backup) {
            writeback(l, c.s[0]);
          } else {
            produced[l].record(c.s[0]);
            produced[l].wait(c.s[2]);
            writeback(l, c.s[2]);
            written[l].record(c.s[2]);
          }
        }
        if (!main_backup) written[L - 1].wait(c.s[0]);
      };
      prepare();
      Executable serial([&]() { enqueue(0); }, c.s[0], capture);
      prepare();
      Executable two([&]() { enqueue(1); }, c.s[0], capture);
      Executable* paths[] = {&serial, &two};
      const char* names[] = {"prefetch_off", "prefetch_on"};
      for (int t = -4; t < c.trials; ++t)
        for (int order = 0; order < 2; ++order) {
          int s = (order + t + 4) % 2;
          prepare();
          // One completion per depth replays. Query feedback persists across
          // replays, and the CPU reference includes every replay; plans cycle
          // through the same layer groups. Final backups validate the last one.
          Event begin(true), end(true);
          auto start = std::chrono::steady_clock::now();
          begin.record(c.s[0]);
          for (int replay = 0; replay < depth; ++replay) paths[s]->run();
          end.record(c.s[0]);
          auto submitted = std::chrono::steady_clock::now();
          HIP(hipEventSynchronize(end));
          auto completed = std::chrono::steady_clock::now();
          float elapsed;
          HIP(hipEventElapsedTime(&elapsed, begin, end));
          Timing tm{elapsed * 1000.0 / depth,
                    std::chrono::duration<double, std::micro>(completed - start).count() / depth,
                    std::chrono::duration<double, std::micro>(submitted - start).count() / depth};
          double e = check();
          if (t >= 0)
            emit("grouped_prefetch", config, names[s], "total", capture, t, tm, e,
                 size_t(L) * (miss + requests) * rb);
        }
    }
  }
}
