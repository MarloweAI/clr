"""Observe launch controls, then exec the unchanged benchmark outside its timers."""
import json, os, sys
CONTROL_KEYS = {
 'HIP_VISIBLE_DEVICES','AMD_DIRECT_DISPATCH','AMD_LOG_LEVEL','AMD_LOG_MASK',
 'GPU_NATIVE_EVENT_WAIT','GPU_NATIVE_EVENT_TRACE','GPU_STREAMOPS_CP_WAIT','GPU_MAX_HW_QUEUES',
 'GPU_GRAPH_NODE_COUNT_PLACEMENT',
 *('GPU_NATIVE_EVENT_DIAGNOSTIC_'+suffix for suffix in (
  'RELAX_COST','MIN_DISPATCHES','POLL_INTERVAL','ORDER_PREWAIT','ZERO_TARGET','DEDUP')),
 *('GPU_GRAPH_DIAGNOSTIC_'+suffix for suffix in (
  'LONGPATH','SIDEWAIT','ENQUEUE_ONLY','DEPTH_ASSIGNMENT','LENGTH_ASSIGNMENT','OMIT_MARKER')),
}
PREFIX='BRIDGE_CHILD_CONTROLS '
def observed_controls():
 keys=CONTROL_KEYS | {k for k in os.environ if k.startswith(('GPU_NATIVE_EVENT_','GPU_GRAPH_','DEBUG_HIP_'))}
 return {k:os.environ.get(k) for k in sorted(keys)}
def audit_receipt(log, controls):
 rows=[json.loads(line[len(PREFIX):]) for line in log.splitlines() if line.startswith(PREFIX)]
 assert len(rows)==1, ('child control receipts',len(rows))
 row=rows[0];assert isinstance(row['pid'],int) and row['pid']>0
 expected={k:controls.get(k) for k in sorted(CONTROL_KEYS | set(controls))}
 assert row['values']==expected, (row['values'],expected)
 return row
if __name__=='__main__':
 assert len(sys.argv)>1
 print(PREFIX+json.dumps({'pid':os.getpid(),'values':observed_controls()},sort_keys=True),file=sys.stderr,flush=True)
 os.execvpe(sys.argv[1],sys.argv[1:],os.environ)
