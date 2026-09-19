#!/usr/bin/env python3
import hashlib,json,shlex,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent;out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
K=R.parent/'hassan-kernel-completion-20260918';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=json.loads((R/'protocol.json').read_text());source=json.loads((R/'source.json').read_text())
for f,h in source.items():assert sha(R/f)==h
for stem,h in spec['libraries'].items():assert sha(Path(spec['lib'])/(stem+'.so'))==h
headers={'hip_graph_internal.hpp':'ba29653dea31a345107cf9774e6033725a197adb367dc5986d382c5f5250052d','hip_internal.hpp':'cf7a0c02657e0441b2961e75c64f0a889393b7a3a10db2b12171e8fcb203c99c'}
for f,h in headers.items():assert sha(K/'build-src/hipamd/src'/f)==h
entries=json.loads((K/'build/compile_commands.json').read_text());entry=next(e for e in entries if e['file'].endswith('/hip_graph.cpp'));args=shlex.split(entry['command']);filtered=[];i=0
while i<len(args):
 if args[i] in ['-o','-c']:i+=2;continue
 filtered.append(args[i]);i+=1
commands=[filtered+['-I'+str(K/'build-src/hipamd/src'),'-fvisibility=hidden','-MMD','-MF',str(out/'extract.d'),'-c',str(R/'extract.cpp'),'-o',str(out/'extract.o')],
 [args[0],'-shared',str(out/'extract.o'),'-L'+str(K/'lib'),'-lamdhip64','-Wl,-rpath,'+str(K/'lib'),'-o',str(out/'extract.so')],
 [args[0],'-O2','-std=c++17','-fPIC','-shared','-I/opt/rocm/include',str(R/'replay.cpp'),'-L'+spec['lib'],'-lhsa-runtime64','-Wl,-rpath,'+spec['lib'],'-o',str(out/'replay.so')]]
for command in commands:
 print('BUILD',shlex.join(command),flush=True);subprocess.run(command,cwd=entry['directory'],check=True)
(out/'build.json').write_text(json.dumps(dict(source=source,headers=headers,compile_commands_sha256=sha(K/'build/compile_commands.json'),commands=commands,helpers={x:sha(out/x) for x in ['extract.so','replay.so']},libraries=spec['libraries']),indent=2)+'\n')
