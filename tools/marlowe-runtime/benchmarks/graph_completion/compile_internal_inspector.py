"""Compile the read-only graph inspector using the matching runtime's host flags."""
import argparse,json,shlex,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
entries=json.loads((a.build.resolve()/'compile_commands.json').read_text())
e=next(x for x in entries if x['file'].endswith('/hip_graph_internal.cpp'))
args=e.get('arguments') or shlex.split(e['command']);out=[];i=0;replaced=0
while i<len(args):
 arg=args[i]
 if arg in ('-o','-MF','-MT','-MQ'):i+=2;continue
 if arg in ('-MD','-MMD','-MP'):i+=1;continue
 if Path(arg)==Path(e['file']):out.append(str(Path(__file__).resolve().with_name('graph_placement_inspect.cpp')));replaced+=1
 else:out.append(arg)
 i+=1
assert replaced==1
# Replacing an in-tree source removes its implicit quoted include directory.
out+=['-I'+str(Path(e['file']).parent),'-o',str(a.output.resolve())]
subprocess.run(out,cwd=e['directory'],check=True)
