#!/usr/bin/env python3
"""Package a clean source build with the matching ROCr, without installing globally."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
RECIPE=Path(__file__).resolve().parent
HIP_COMMIT='bc9af25177f96c0fea93198b89cf4c3cf08f3ea3'
HSA_SHA='b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(p,*args):return subprocess.check_output(['git','-C',str(p),*args],text=True).strip()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['source','hip','build','output']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--rocm',type=Path,default=Path('/opt/rocm'));a=p.parse_args()
 source=a.source.resolve();build=a.build.resolve();out=a.output.resolve();hip_headers=a.hip.resolve()
 assert not git(source,'status','--porcelain'), 'Build and package a committed clean checkout'
 assert git(hip_headers,'rev-parse','HEAD')==HIP_COMMIT and not git(hip_headers,'status','--porcelain')
 assert f'CMAKE_HOME_DIRECTORY:INTERNAL={source}\n' in (build/'CMakeCache.txt').read_text()
 hip=(build/'hipamd/lib/libamdhip64.so').resolve(strict=True)
 hsa=(a.rocm/'lib/libhsa-runtime64.so').resolve(strict=True);assert sha(hsa)==HSA_SHA
 out.mkdir(parents=True,exist_ok=False);(out/'lib').mkdir();(out/'licenses').mkdir()
 m={'release':out.name,'clr_commit':git(source,'rev-parse','HEAD'),'hip_commit':HIP_COMMIT,'architecture':'gfx950','qualified_for_production':False,'default_enabled':False,'libraries':{},'aliases':{},'enabled_profile':{'GPU_NATIVE_EVENT_WAIT':'1','GPU_GRAPH_NODE_COUNT_PLACEMENT':'1','GPU_NATIVE_EVENT_TRACE':'0'},'disabled_profile':{'GPU_NATIVE_EVENT_WAIT':'0','GPU_GRAPH_NODE_COUNT_PLACEMENT':'0'},'build_base_image':os.environ.get('RUNTIME_BUILD_BASE_IMAGE'),'compile_commands_sha256':sha(build/'compile_commands.json')}
 for library,aliases in [(hip,['libamdhip64.so','libamdhip64.so.7']),(hsa,['libhsa-runtime64.so','libhsa-runtime64.so.1'])]:
  shutil.copy2(library,out/'lib'/library.name);m['libraries'][library.name]=sha(library)
  for alias in aliases:
   assert alias!=library.name,'Expected the versioned library target'
   (out/'lib'/alias).symlink_to(library.name);m['aliases'][alias]=library.name
 for f in ['run','verify.py','README.md']:shutil.copy2(RECIPE/f,out/f)
 for source_license,dest in [(source/'LICENSE.md','CLR-LICENSE.md'),(hip_headers/'LICENSE.md','HIP-LICENSE.md'),(RECIPE/'ROCr-LICENSE.txt','ROCr-LICENSE.txt')]:shutil.copy2(source_license,out/'licenses'/dest)
 m['recipe_sha256']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and 'lib' not in f.relative_to(out).parts}
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 subprocess.run(['python3',str(out/'verify.py'),'--files-only'],check=True)
 print(json.dumps({'package':str(out),'manifest_sha256':sha(out/'manifest.json'),'libraries':m['libraries']},indent=2))
if __name__=='__main__':main()
