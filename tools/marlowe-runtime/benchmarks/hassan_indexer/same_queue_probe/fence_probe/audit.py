#!/usr/bin/env python3
import csv, hashlib, json, struct, sys
from pathlib import Path

def audit(out):
    out = Path(out).resolve(); root = Path(__file__).resolve().parent
    source = json.loads((root/'source.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, expected in source['sources'].items(): assert sha(root/name) == expected, name
    identity = json.loads((out/'identity.json').read_text())
    assert identity['source'] == source and identity['node'] == 'marlowe-mi355x-2'
    device = json.loads((out/'device.json').read_text())
    assert device['agent'] == 'gfx950' and device['compute_units'] == 256
    assert device['private_bytes'] == device['static_group_bytes'] == 0
    configs = {f'edge_r{r}_a{a}': (2,r,a,2,1,0,0) for r in (2,1,0) for a in (2,1,0)}
    configs.update(agent_pair=(1,1,1,1,1,0,0), none_pair=(0,0,0,0,1,0,0),
                   none_pair_first_unordered=(0,0,0,0,0,0,0),
                   agent_pair_first_unordered=(1,1,1,1,0,0,0),
                   system_pair_first_unordered=(2,2,2,2,0,0,0), serial_system=(2,2,2,2,1,1,0),
                   serial_none=(0,0,0,0,1,1,0), two_queue_system=(2,2,2,2,1,0,1))
    rows = list(csv.DictReader((out/'trials.csv').open()))
    assert len(rows) == 272
    seen, queue0, queue1, totals = set(), set(), set(), {}
    samples_count = 0
    for i,row in enumerate(rows):
        v = lambda k: int(row[k])
        assert v('id') == i and v('epoch') == i+1
        cfg = configs[row['case']]
        assert tuple(v(k) for k in ('a0','r0','a1','r1','first_ordered','serial','two_queues')) == cfg
        key=(v('round'),row['case'],row['geometry'],v('reverse'))
        assert key not in seen; seen.add(key)
        epoch,q,k = v('epoch'),v('blocks_q'),v('blocks_k')
        assert (q,k,v('lds')) == ((1,1,512) if row['geometry'] == 'one_block' else (256,24,61440))
        queue0.add(v('queue0'))
        if v('two_queues'): queue1.add(v('queue1')); assert v('queue0') != v('queue1')
        else: assert v('queue1') == 0 and row['packets1'] == '' and v('first1') == v('last1') == 0
        assert v('doorbells') == 1+v('two_queues') and v('correct') == 1
        states = struct.unpack('<8Q',(out/row['states']).read_bytes())
        assert states == (epoch,epoch,epoch*1024+1,epoch*1024+2,q,k,q,k)
        samples = list(struct.iter_unpack('<6Q',(out/row['trace']).read_bytes()))
        assert len(samples) == q+k
        for role,count in enumerate((q,k)):
            for block,s in enumerate(samples[(q if role else 0):(q if role else 0)+count]):
                start,end,saw,ok,value,b = s
                assert start and end>=start and ok==1 and value==epoch*1024+role+1 and b==block
                assert saw in (0,1) and (not block or saw==0)
                samples_count += 1
        root_samples = (samples[0],samples[q])
        overlap = int(all(s[2] for s in root_samples))
        assert overlap == v('overlap')
        if v('serial'):
            assert not overlap and root_samples[v('reverse')][2] == 0 and root_samples[1-v('reverse')][2] == 1
        gates=[]
        for which in range(1+v('two_queues')):
            packets=(out/row[f'packets{which}']).read_bytes()
            count=3 if v('two_queues') else 4
            assert len(packets)==count*64 and v(f'last{which}')-v(f'first{which}')+1==count
            for index in range(count):
                packet=packets[index*64:(index+1)*64]
                head,setup=struct.unpack_from('<HH',packet)
                kind,ordered,acquire,release=head&255,(head>>8)&1,(head>>9)&3,(head>>11)&3
                signal,=struct.unpack_from('<Q',packet,56)
                if index in (0,count-1):
                    entry=index==0
                    assert kind==3 and ordered==1 and packet[2:8]==bytes(6) and packet[16:56]==bytes(40)
                    gate,=struct.unpack_from('<Q',packet,8)
                    if entry and v('two_queues'): assert gate; gates.append(gate)
                    else: assert gate==0
                    assert (acquire,release)==((2,0) if entry else (0,2)) and bool(signal)==(not entry)
                else:
                    position=which if v('two_queues') else index-1
                    role=position^v('reverse')
                    expected_ordered=cfg[4] if position==0 else cfg[5]
                    assert kind==2 and ordered==expected_ordered and signal==0 and setup==1
                    assert (acquire,release)==cfg[position*2:position*2+2]
                    assert struct.unpack_from('<3H',packet,4)==(128,1,1)
                    assert struct.unpack_from('<3I',packet,12)==((q if role==0 else k)*128,1,1)
                    assert struct.unpack_from('<2I',packet,24)==(0,v('lds'))
                    assert struct.unpack_from('<Q',packet,32)[0]==device['kernel_object']
                    assert struct.unpack_from('<Q',packet,40)[0]
        if v('two_queues'): assert len(gates)==2 and gates[0]==gates[1]
        cell=totals.setdefault(row['geometry']+'/'+row['case'],dict(trials=0,overlap=0))
        cell['trials']+=1;cell['overlap']+=overlap
    assert len(queue0)==len(queue1)==1 and queue0.isdisjoint(queue1)
    assert seen=={(r,c,g,o) for r in range(4) for c in configs for g in ('one_block','qk_geometry') for o in (0,1)}
    assert all(cell['trials']==8 for cell in totals.values())
    maps=(out/'maps.txt').read_text();assert 'libamdhip64' not in maps
    paths={line.split()[-1] for line in maps.splitlines() if 'libhsa-runtime64' in line};assert len(paths)==1
    receipt_path=out/'receipt.json'
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text());assert receipt['hsa_path'] in paths and receipt['hsa_sha256']==source['hsa_sha256']
        for name,expected in receipt['files'].items():assert sha(out/name)==expected,name
    positive=all(totals[g+'/two_queue_system']['overlap']==8 for g in ('one_block','qk_geometry'))
    result=dict(correctness='PASS',positive_control='PASS' if positive else 'FAIL',trials=272,samples=samples_count,cells=totals,
                interpretation='Dispatch-fence capability discriminator only, not original Q/K performance.')
    print(json.dumps(result,indent=2));return result

if __name__=='__main__':
    result=audit(sys.argv[1]);(Path(sys.argv[1])/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
