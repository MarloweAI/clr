from pathlib import Path
import json,hashlib,shutil
G=Path(__file__).resolve().parent;R=G/'src'
manifest=json.loads((G/'source-manifest-v7.json').read_text())
for f,h in manifest.items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h,f
paths=['rocclr/device/device.hpp','rocclr/device/rocm/rocvirtual.hpp','rocclr/device/rocm/rocvirtual.cpp','rocclr/platform/command.hpp','rocclr/utils/flags.hpp','hipamd/src/hip_graph_internal.cpp']
for f in paths:
 p=G/'v7-source-snapshot'/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/f,p)
def edit(f,old,new):
 p=R/f;s=p.read_text();assert s.count(old)==1,(f,s.count(old),old[:100]);p.write_text(s.replace(old,new))
f='rocclr/device/device.hpp'
edit(f,'  virtual bool supportsGraphFrontier() const { return false; }','''  struct GraphFrontierTail { uint64_t queue; uint64_t signal; };
  struct GraphFrontierBoundary {
    const amd::Device* device = nullptr;
    std::vector<GraphFrontierTail> tails;
  };
  virtual bool supportsGraphFrontier() const { return false; }''')
edit(f,'uint64_t completion, bool system_acquire) { return nullptr; }','uint64_t completion, bool system_acquire, bool agent_release = false) { return nullptr; }')
edit(f,'  virtual void materializeGraphFrontier(amd::Marker&, uint64_t) { std::abort(); }','''  virtual void materializeGraphFrontier(amd::Marker&, uint64_t) { std::abort(); }
  virtual void materializeGraphBoundary(amd::Marker&, const GraphFrontierBoundary&) {
    std::abort();
  }''')
f='rocclr/device/rocm/rocvirtual.hpp'
edit(f,'uint64_t completion, bool system_acquire) override;','uint64_t completion, bool system_acquire, bool agent_release = false) override;')
edit(f,'  void materializeGraphFrontier(amd::Marker& command, uint64_t completion) override;','''  void materializeGraphFrontier(amd::Marker& command, uint64_t completion) override;
  void materializeGraphBoundary(amd::Marker& command,
                                const GraphFrontierBoundary& boundary) override;''')
f='rocclr/platform/command.hpp'
edit(f,'  virtual uint64_t graphFrontier() const { return 0; }','''  virtual uint64_t graphFrontier() const { return 0; }
  virtual const device::VirtualDevice::GraphFrontierBoundary* graphBoundary() const {
    return nullptr;
  }''')
edit(f,'  uint64_t frontier_ = 0;\n  static void completed','  uint64_t frontier_ = 0;\n  const device::VirtualDevice::GraphFrontierBoundary* boundary_ = nullptr;\n  static void completed')
edit(f,'    frontier_ = owner.graphFrontier();','    frontier_ = owner.graphFrontier();\n    boundary_ = owner.graphBoundary();')
edit(f,'    device.materializeGraphFrontier(*this, frontier_);','''    if (boundary_ != nullptr) device.materializeGraphBoundary(*this, *boundary_);
    else device.materializeGraphFrontier(*this, frontier_);''')
edit(f,'  uint64_t frontier_;\n  bool published_ = false;','''  uint64_t frontier_;  // Also a nonzero private-boundary tag when no final token is produced.
  device::VirtualDevice::GraphFrontierBoundary boundary_;
  bool distributed_ = false;
  bool published_ = false;''')
edit(f,'  uint64_t graphFrontier() const override { return frontier_; }','''  uint64_t graphFrontier() const override { return frontier_; }
  void sealGraphBoundary(device::VirtualDevice::GraphFrontierBoundary&& boundary) {
    assert(!distributed_ && boundary.device != nullptr && !boundary.tails.empty());
    boundary_ = std::move(boundary);  // Prepared before publication; move cannot allocate.
    distributed_ = true;
  }
  const device::VirtualDevice::GraphFrontierBoundary* graphBoundary() const override {
    return distributed_ ? &boundary_ : nullptr;
  }''')
f='rocclr/utils/flags.hpp'
edit(f,'release(bool, GPU_GRAPH_DIAGNOSTIC_FRONTIER, false,                         \\\n','release(bool, GPU_GRAPH_DIAGNOSTIC_FRONTIER_DISTRIBUTED, false,             \\\n        "Diagnostic: direct physical-queue graph tails and public bridge")    \\\nrelease(bool, GPU_GRAPH_DIAGNOSTIC_FRONTIER, false,                         \\\n')
f='rocclr/device/rocm/rocvirtual.cpp'
edit(f,'const std::vector<uint64_t>& dependencies, uint64_t completion, bool system_acquire) {','const std::vector<uint64_t>& dependencies, uint64_t completion, bool system_acquire,\n    bool agent_release) {')
edit(f,'    RocGraphFrontierBatch::Packet copy;\n    std::memcpy(&copy, &packet, sizeof(copy));','''    if (i + 1 == packets.size() && agent_release) {
      constexpr uint16_t mask = ((1u << HSA_PACKET_HEADER_WIDTH_SCRELEASE_FENCE_SCOPE) - 1)
                                << HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE;
      const auto scope = (packet.header & mask) >> HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE;
      if (scope < HSA_FENCE_SCOPE_AGENT) {
        packet.header = (packet.header & ~mask) |
            (HSA_FENCE_SCOPE_AGENT << HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE);
      }
      if (GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE) {
        fprintf(stderr, "GRAPH_FRONTIER_TAIL_RELEASE signal=%llu scope=%u\\n",
                static_cast<unsigned long long>(completion),
                (packet.header & mask) >> HSA_PACKET_HEADER_SCRELEASE_FENCE_SCOPE);
      }
    }
    RocGraphFrontierBatch::Packet copy;
    std::memcpy(&copy, &packet, sizeof(copy));''')
edit(f,'bool VirtualGPU::resetGraphSignalArena(GraphSignalArena& storage,','''void VirtualGPU::materializeGraphBoundary(amd::Marker& command,
                                           const GraphFrontierBoundary& boundary) {
  assert(boundary.device == &device() && !boundary.tails.empty());
  assert(command_ == nullptr && timestamp_ == nullptr);
  profilingBegin(command);
  // Stack packets only: this descriptor and its signal ownership were sealed
  // before the command entered the host batch. Ordered packets AND all tails.
  for (size_t i = 0; i < boundary.tails.size(); i += 5) {
    hsa_barrier_and_packet_t barrier{};
    barrier.header = kNopPacketHeader;
    if (i + 5 >= boundary.tails.size()) {
      barrier.header |= HSA_FENCE_SCOPE_AGENT << HSA_PACKET_HEADER_SCACQUIRE_FENCE_SCOPE;
    }
    for (size_t j = 0; j < 5 && i + j < boundary.tails.size(); ++j) {
      barrier.dep_signal[j].handle = boundary.tails[i + j].signal;
    }
    RocGraphFrontierBatch::Packet packet;
    std::memcpy(&packet, &barrier, sizeof(packet));
    publishGraphFrontierPackets(&packet, 1);
  }
  if (GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE) {
    fprintf(stderr, "GRAPH_FRONTIER_PUBLIC command=%p tails=%zu physical=%llu\\n",
            static_cast<void*>(&command), boundary.tails.size(),
            static_cast<unsigned long long>(getQueueID()));
  }
  // Ordinary SYSTEM-acquire/release completion exposes every private lane to
  // host callbacks, events and SDMA. Private tokens never enter HwQueueTracker.
  releaseGpuMemoryFence(true);
  profilingEnd();
}

bool VirtualGPU::resetGraphSignalArena(GraphSignalArena& storage,''')
f='hipamd/src/hip_graph_internal.cpp'
edit(f,'  using Batch = amd::device::VirtualDevice::GraphFrontierBatch;','''  using Batch = amd::device::VirtualDevice::GraphFrontierBatch;
  using Boundary = amd::device::VirtualDevice::GraphFrontierBoundary;
  const bool distributed = GPU_GRAPH_DIAGNOSTIC_FRONTIER_DISTRIBUTED;''')
edit(f,'    std::unique_ptr<Batch> prefix_join;\n  };','    std::unique_ptr<Batch> prefix_join;\n    Boundary prefix_boundary;\n  };')
edit(f,'    const bool chained = snapshot != nullptr && snapshot->graphFrontier() != 0;','''    const auto* prior_boundary = snapshot == nullptr ? nullptr : snapshot->graphBoundary();
    const bool compatible_boundary = prior_boundary == nullptr ||
        (distributed && prior_boundary->device == &launch_stream->device() &&
         !prior_boundary->tails.empty());
    const bool chained = snapshot != nullptr && snapshot->graphFrontier() != 0 &&
        compatible_boundary;''')
edit(f,'    auto empty_join = launch_stream->vdev()->prepareGraphFrontierJoin({}, frontier, true);\n    bool prepared = entry_plan != nullptr && empty_join != nullptr;','''    auto empty_join = distributed ? nullptr :
        launch_stream->vdev()->prepareGraphFrontierJoin({}, frontier, true);
    Boundary empty_boundary;
    empty_boundary.device = &launch_stream->device();
    if (distributed) {
      if (chained && prior_boundary != nullptr) empty_boundary.tails = prior_boundary->tails;
      else empty_boundary.tails.push_back({launch_queue, chained ? snapshot->graphFrontier() : entry});
    }
    bool prepared = entry_plan != nullptr && (distributed || empty_join != nullptr);''')
edit(f,'        if (first && queue != launch_queue) dependencies.push_back(entry_dependency);','''        if (first && distributed && chained && prior_boundary != nullptr) {
          // Every old physical queue must precede every new root. Same-queue
          // order covers its own tail; all foreign tails are explicit waits.
          for (const auto& tail : prior_boundary->tails) {
            if (tail.queue != queue) dependencies.push_back(tail.signal);
          }
        } else if (first && queue != launch_queue) {
          dependencies.push_back(entry_dependency);
        }
        if (GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE && distributed && first) {
          fprintf(stderr, "GRAPH_FRONTIER_ENTRY graph=%p serial=%llu physical=%llu prior_tails=%zu waits=%zu\\n",
                  static_cast<void*>(this), static_cast<unsigned long long>(serial),
                  static_cast<unsigned long long>(queue),
                  chained && prior_boundary != nullptr ? prior_boundary->tails.size() : size_t(0),
                  dependencies.size());
        }''')
edit(f,'dependencies, generation->arena->handles.at(id), first);','dependencies, generation->arena->handles.at(id), first, distributed);')
edit(f,'''        auto join = launch_stream->vdev()->prepareGraphFrontierJoin(terminal, frontier, true);
        if (packets == nullptr || join == nullptr) { prepared = false; break; }
        plans.push_back({stream, id, std::move(packets), std::move(join)});''','''        auto join = distributed ? nullptr :
            launch_stream->vdev()->prepareGraphFrontierJoin(terminal, frontier, true);
        Boundary boundary;
        boundary.device = &launch_stream->device();
        if (distributed) {
          boundary.tails.reserve(tails.size());
          for (const auto& tail : tails) boundary.tails.push_back({tail.first, tail.second});
        }
        if (packets == nullptr || (!distributed && join == nullptr)) { prepared = false; break; }
        plans.push_back({stream, id, std::move(packets), std::move(join), std::move(boundary)});''')
edit(f,'''    // From here every exit publishes a prebuilt all-touched-lane join and enters
    // the normal host batch. No resource allocation is needed by the raw backend.''','''    // From here every exit seals the exact touched prefix (or publishes its
    // prebuilt central join) and enters the host batch. No further allocation.''')
edit(f,'''    launch_stream->vdev()->publishGraphFrontierBatch(
        submitted == 0 ? *empty_join : *plans.at(submitted - 1).prefix_join);
    command->enqueue();''','''    if (distributed) {
      auto& boundary = submitted == 0 ? empty_boundary : plans.at(submitted - 1).prefix_boundary;
      if (GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE) {
        for (const auto& tail : boundary.tails) {
          fprintf(stderr, "GRAPH_FRONTIER_SEAL graph=%p serial=%llu physical=%llu signal=%llu\\n",
                  static_cast<void*>(this), static_cast<unsigned long long>(serial),
                  static_cast<unsigned long long>(tail.queue),
                  static_cast<unsigned long long>(tail.signal));
        }
      }
      command->sealGraphBoundary(std::move(boundary));
    } else {
      launch_stream->vdev()->publishGraphFrontierBatch(
          submitted == 0 ? *empty_join : *plans.at(submitted - 1).prefix_join);
    }
    command->enqueue();''')
print('Implemented distributed boundary; not built or qualified')
