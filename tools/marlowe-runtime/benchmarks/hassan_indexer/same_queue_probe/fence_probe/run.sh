#!/bin/bash
set -euo pipefail
root=/workspace/home/sasha/amd-runtime-production/iterations/hassan-same-queue-20260919/fence_probe
cd "$root"
out="$root/results-j${SLURM_JOB_ID}"
mkdir "$out"
python3 - "$out" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
out=Path(sys.argv[1]);r=Path.cwd();s=json.loads((r/'source.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for f,h in s['sources'].items():assert sha(r/f)==h,f
assert sha(Path('/opt/rocm/lib/libhsa-runtime64.so'))==s['hsa_sha256']
identity=dict(source=s,job=os.environ['SLURM_JOB_ID'],node=os.uname().nodename,kernel=os.uname().release,affinity=sorted(os.sched_getaffinity(0)),visibility={k:v for k,v in os.environ.items() if 'VISIBLE_DEVICES' in k or k in ['SLURM_JOB_GPUS','SLURM_STEP_GPUS']})
assert identity['node']=='marlowe-mi355x-2'
(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
print('PREFLIGHT PASS',flush=True)
PY
/opt/rocm/bin/hipcc --genco -O2 --offload-arch=gfx950 probes.cpp -o "$out/probes.bundle"
/opt/rocm/llvm/bin/clang-offload-bundler --type=o --input="$out/probes.bundle" --list > "$out/bundle-targets.txt"
python3 - "$out" <<'PY'
import subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);targets=(p/'bundle-targets.txt').read_text().splitlines();selected=[x for x in targets if x in ('hip-amdgcn-amd-amdhsa--gfx950','hipv4-amdgcn-amd-amdhsa--gfx950')];assert len(selected)==1,targets
subprocess.run(['/opt/rocm/llvm/bin/clang-offload-bundler','--type=o','--unbundle','--input='+str(p/'probes.bundle'),'--output='+str(p/'probes.hsaco'),'--targets='+selected[0]],check=True)
assert (p/'probes.hsaco').read_bytes()[:4]==b'\x7fELF'
PY
/opt/rocm/llvm/bin/clang++ -O2 -std=c++17 packet_layers.cpp -I/opt/rocm/include -L/opt/rocm/lib -Wl,-rpath,/opt/rocm/lib -lhsa-runtime64 -pthread -o "$out/packet_layers"
/opt/rocm/llvm/bin/llvm-readelf --notes "$out/probes.hsaco" > "$out/code-object-notes.txt"
/opt/rocm/llvm/bin/llvm-objdump -d "$out/probes.hsaco" > "$out/isa.txt"
python3 - "$out" <<'PY'
import os,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);env={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','HSA_','AMD_LOG','ROC_GLOBAL_CU_MASK'))}
env.pop('LD_PRELOAD',None);env.pop('LD_DEBUG',None);env['LD_LIBRARY_PATH']='/opt/rocm/lib'
subprocess.run([str(p/'packet_layers'),str(p/'probes.hsaco'),str(p)],env=env,check=True)
PY
python3 audit.py "$out"
python3 - "$out" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);source=json.loads(Path('source.json').read_text());maps=(p/'maps.txt').read_text();paths={x.split()[-1] for x in maps.splitlines() if 'libhsa-runtime64' in x};assert len(paths)==1
actual=paths.pop();assert hashlib.sha256(Path(actual).read_bytes()).hexdigest()==source['hsa_sha256'];assert 'libamdhip64' not in maps
receipt=dict(hsa_path=actual,hsa_sha256=source['hsa_sha256'],hip_runtime_loaded=False,files={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir() if x.is_file()})
(p/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
audit=json.loads((p/'audit.json').read_text());(p/'COMPLETE').write_text('CORRECTNESS_PASS CONTROL_'+audit['positive_control']+'\n')
PY
