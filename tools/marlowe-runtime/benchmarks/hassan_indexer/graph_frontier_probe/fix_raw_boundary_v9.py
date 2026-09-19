from pathlib import Path
import json,hashlib,shutil
G=Path(__file__).resolve().parent;R=G/'src'
for f,h in json.loads((G/'source-manifest-v8.json').read_text()).items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h,f
for f in ['rocclr/platform/command.hpp','rocclr/platform/command.cpp','rocclr/device/rocm/rocvirtual.cpp']:
 p=G/'v8-source-snapshot'/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/f,p)
p=R/'rocclr/platform/command.hpp';s=p.read_text();old='  virtual Command* takeGraphFrontierBridge() { return nullptr; }';assert s.count(old)==1;s=s.replace(old,old+'\n  // Caller holds this HostQueue virtual-device execution lock.\n  void materializeGraphPredecessor(bool distributed_only = false);');p.write_text(s)
p=R/'rocclr/platform/command.cpp';s=p.read_text();block='''    if (!defersGraphRetirement() && !consumesGraphFrontier()) {
      auto* predecessor = queue_->getLastQueuedCommand(false);
      if (predecessor != nullptr && predecessor->graphFrontier() != 0) {
        auto* bridge = predecessor->takeGraphFrontierBridge();
        assert(bridge != nullptr);
        bridge->enqueue();  // Recursive execution lock; no graph/notification lock.
        bridge->release();
      }
    }''';assert s.count(block)==1;s=s.replace(block,'    materializeGraphPredecessor();')
old='void Command::enqueue() {';assert s.count(old)==1;s=s.replace(old,'''void Command::materializeGraphPredecessor(bool distributed_only) {
  assert(queue_ != nullptr);
  if (defersGraphRetirement() || consumesGraphFrontier()) return;
  auto* predecessor = queue_->getLastQueuedCommand(false);
  if (predecessor != nullptr && predecessor->graphFrontier() != 0 &&
      (!distributed_only || predecessor->graphBoundary() != nullptr)) {
    auto* bridge = predecessor->takeGraphFrontierBridge();
    assert(bridge != nullptr);
    // Recursive execution lock, empty event wait list, no notify_lock. This
    // must also run before captured packets that bypass Command::enqueue.
    bridge->enqueue();
    bridge->release();
  }
}

void Command::enqueue() {''');p.write_text(s)
p=R/'rocclr/device/rocm/rocvirtual.cpp';s=p.read_text();old='''  amd::ScopedLock lock(execution());
  if (graph_completion == 0 && vcmd->graphKernelRetirementRequested()) {''';assert s.count(old)==1;s=s.replace(old,'''  amd::ScopedLock lock(execution());
  assert(vcmd->queue()->vdev() == this);
  // Raw graph batches can publish before their accumulator is enqueued. A
  // distributed predecessor has no central launch-queue join, so import its
  // complete boundary here under the publication lock, including single roots.
  vcmd->materializeGraphPredecessor(true);
  if (graph_completion == 0 && vcmd->graphKernelRetirementRequested()) {''');p.write_text(s)
print('Added raw captured-batch predecessor bridge before all publication')
