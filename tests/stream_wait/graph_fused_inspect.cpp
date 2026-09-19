// Compile with the candidate runtime's own host compiler flags and headers.
// No runtime export or timed tracing is added; inspect the exact executable
// created by the public HIP APIs in the untimed qualification fixture.
#include "hip_graph_internal.hpp"
namespace hip {
struct GraphPlacementTestAccess {
  static int entryDevice(hipGraphExec_t exec) {
    return reinterpret_cast<GraphExec*>(exec)->entry_fused_device_id_;
  }
  static int device(hipGraphExec_t exec) {
    return reinterpret_cast<GraphExec*>(exec)->assignment_device_id_;
  }
};
}
extern "C" int placement_device(hipGraphExec_t exec) {
  return hip::GraphPlacementTestAccess::device(exec);
}

extern "C" int entry_device(hipGraphExec_t exec) {
  return hip::GraphPlacementTestAccess::entryDevice(exec);
}
