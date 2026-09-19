// Read-only diagnostic bridge. Compile with the exact K runtime's flags and headers.
#include "hip_graph_internal.hpp"
#include <cstring>
#include <stdexcept>
#include <unordered_map>
extern "C" __attribute__((visibility("default")))
int extract_packets(void* raw_exec, unsigned expected, unsigned char* packets,
                    unsigned* dependencies, unsigned* argument_sizes) {
  try {
    auto* graph = reinterpret_cast<hip::GraphExec*>(raw_exec);
    const auto& nodes = static_cast<hip::Graph*>(graph)->GetNodes();
    if (nodes.size() != expected || expected > 1024) throw std::runtime_error("node count/ABI mismatch");
    std::unordered_map<hip::Node,unsigned> indices;
    for (unsigned i=0;i<expected;++i) indices.emplace(nodes[i],i);
    for (unsigned i=0;i<expected;++i) {
      auto* node=nodes[i];
      if (node->GetType()!=hipGraphNodeTypeKernel || node->GetAqlPackets().size()!=1)
        throw std::runtime_error("not exactly one captured dispatch per kernel");
      const auto& deps=node->GetDependencies();
      if (deps.size()!=0 && deps.size()!=2) throw std::runtime_error("not the full two-root join DAG");
      dependencies[3*i]=deps.size();
      for (unsigned j=0;j<deps.size();++j) dependencies[3*i+1+j]=indices.at(deps[j]);
      argument_sizes[i]=node->GetKernargSegmentByteSize();
      if (!argument_sizes[i] || argument_sizes[i]>4096) throw std::runtime_error("invalid kernarg size");
      std::memcpy(packets+64*i,node->GetAqlPackets()[0],64);
    }
    return 0;
  } catch(const std::exception& e) { std::fprintf(stderr,"EXTRACT_ERROR %s\n",e.what()); return 1; }
}
extern "C" __attribute__((visibility("default")))
int hip_replay_loop(void* graph, void* stream, unsigned count) {
  for (unsigned i=0;i<count;++i) {
    hipError_t e=hipGraphLaunch(reinterpret_cast<hipGraphExec_t>(graph),reinterpret_cast<hipStream_t>(stream));
    if (e!=hipSuccess) return int(e);
  }
  return 0;
}
