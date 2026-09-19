#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys,os,shutil
w=Path(__file__).resolve().parent;rev=sys.argv[1];assert rev in ['v7']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=w/('build-src-'+rev);out=w/('build-'+rev);lib=w/('lib-'+rev)
assert not src.exists() and not out.exists() and not lib.exists()
manifest=json.loads((w/('source-manifest-'+rev+'.json')).read_text())
base=w.parent/'c1-runtime-recovery-20260917/release-clr'
commands=[['git','clone','--shared',str(base),str(src)],['git','-C',str(src),'checkout','--detach','cab5670a350678f2b0a6feb388fcbbca56c426a1'],['git','-C',str(src),'apply',str(w/('full-'+rev+'.patch'))]]
for cmd in commands:print('BUILD',cmd,flush=True);subprocess.run(cmd,check=True)
for f,h in manifest.items():assert sha(src/f)==h,f
release=w.parent/'native-wait-neutral-20260917/release8-build';os.environ['PYTHONPATH']=str(release/'python-deps')
commands.extend([['cmake','-S',str(src),'-B',str(out),'-DCLR_BUILD_HIP=ON','-DCLR_BUILD_OCL=OFF','-DHIP_PLATFORM=amd','-D__HIP_ENABLE_PCH=OFF','-DHIP_COMMON_DIR='+str(release/'hip'),'-DCMAKE_PREFIX_PATH=/opt/rocm','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang','-DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++'],['cmake','--build',str(out),'-j8']])
for cmd in commands[3:]:print('BUILD',cmd,flush=True);subprocess.run(cmd,check=True)
lib.mkdir();shutil.copy2((out/'hipamd/lib/libamdhip64.so').resolve(strict=True),lib/'libamdhip64.so')
hsa=w.parent/'hassan-signal-locality-20260919/lib/libhsa-runtime64.so'
assert sha(hsa)=='2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12'
shutil.copy2(hsa.resolve(strict=True),lib/'libhsa-runtime64.so')
(lib/'libamdhip64.so.7').symlink_to('libamdhip64.so');(lib/'libhsa-runtime64.so.1').symlink_to('libhsa-runtime64.so')
receipt=dict(revision=rev,source_manifest_sha256=sha(w/('source-manifest-'+rev+'.json')),full_patch_sha256=sha(w/('full-'+rev+'.patch')),candidate_patch_sha256=sha(w/('candidate-'+rev+'.patch')),commands=commands,libraries={f:sha(lib/f) for f in ['libamdhip64.so','libhsa-runtime64.so']},compiler=subprocess.check_output(['/opt/rocm/llvm/bin/clang++','--version'],text=True))
(w/('runtime-build-'+rev+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');(w/('BUILD_COMPLETE-'+rev)).write_text('PASS\n');print('BUILD_COMPLETE',json.dumps(receipt),flush=True)
