#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys,os
r=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=json.loads((r/'rocr-source-manifest.json').read_text())
for name,h in manifest.items():assert sha(r/'rocr-source'/name)==h,name
out=r/'rocr-build-v4';out.mkdir(exist_ok=False)
os.environ['PATH']=str(r/'tool-bin')+':'+os.environ['PATH']
commands=[['cmake','-S',str(r/'rocr-source'),'-B',str(out),'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_PREFIX_PATH=/opt/rocm','-DClang_DIR='+str(r/'tool-cmake'),'-DLLVM_DIR='+str(r/'tool-cmake'),'-DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang','-DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DROCM_PATCH_VERSION=70204'],['cmake','--build',str(out),'--parallel','8']]
for command in commands:
 print('BUILD',command,flush=True);subprocess.run(command,check=True)
lib=(out/'rocr/lib/libhsa-runtime64.so').resolve(strict=True)
receipt=dict(source_manifest_sha256=sha(r/'rocr-source-manifest.json'),patch_sha256=sha(r/'signal-locality.patch'),tool_cmake={p.name:sha(p) for p in sorted((r/'tool-cmake').glob('*'))},tool_hashes={str(p):sha(p) for p in [Path('/opt/rocm/llvm/bin/clang'),Path('/opt/rocm/llvm/bin/llvm-objcopy'),r/'tool-bin/xxd']},library=str(lib),sha256=sha(lib),commands=commands,ldd=subprocess.check_output(['ldd',str(lib)],text=True))
(r/'runtime-build.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('BUILD_COMPLETE',json.dumps(receipt),flush=True)
