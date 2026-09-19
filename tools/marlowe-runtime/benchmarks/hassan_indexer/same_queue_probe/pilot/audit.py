#!/usr/bin/env python3
import csv, hashlib, json, struct, sys
from pathlib import Path

def audit(out):
    out = Path(out).resolve()
    root = Path(__file__).resolve().parent
    source = json.loads((root/'source.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, expected in source['sources'].items():
        assert sha(root/name) == expected, ('source changed', name)
    identity = json.loads((out/'identity.json').read_text())
    assert identity['source'] == source and identity['node'] == 'marlowe-mi355x-2'
    device = json.loads((out/'device.json').read_text())
    assert device['agent'] == 'gfx950' and device['compute_units'] == 256
    assert device['private_bytes'] == device['static_group_bytes'] == 0
    publisher = json.loads((out/'publisher.json').read_text())
    assert publisher == dict(queue_count=1, queue_size=4096,
                            oversize_rejected_before_reservation=True,
                            full_capacity_completed=True, trials=64)
    rows = list(csv.DictReader((out/'trials.csv').open()))
    assert len(rows) == 64
    queues, configs, totals = set(), set(), {}
    total_samples = wraps = 0
    previous_last = None
    for i, row in enumerate(rows):
        integer = lambda k: int(row[k])
        assert integer('id') == i and integer('epoch') == i+1
        epoch, layers = integer('epoch'), integer('layers')
        q, k = integer('blocks_q'), integer('blocks_k')
        geometry, mode = row['geometry'], row['mode']
        assert (q,k,integer('lds')) == ((1,1,512) if geometry == 'one_block' else (256,24,61440))
        config = (integer('round'), geometry, layers, integer('reverse'), mode)
        assert config not in configs
        configs.add(config); queues.add(integer('queue_id'))
        assert integer('last') - integer('first') + 1 == 3*layers
        if previous_last is not None: assert integer('first') == previous_last+1
        previous_last = integer('last')
        assert integer('first')-integer('read_before')+3*layers <= 4096
        assert integer('wrapped') == int(integer('first') % 4096 + 3*layers > 4096)
        assert integer('doorbells') == 1 and integer('correct') == 1
        wraps += integer('wrapped')
        data = (out/row['trace']).read_bytes()
        samples = list(struct.iter_unpack('<6Q', data))
        states = list(struct.iter_unpack('<8Q', (out/row['states']).read_bytes()))
        packets = (out/row['packets']).read_bytes()
        assert len(samples) == layers*(q+k) and len(states) == layers and len(packets) == layers*3*64
        overlap = 0
        for layer in range(layers):
            assert states[layer] == (epoch,epoch,epoch*1024+layer*2+1,epoch*1024+layer*2+2,q,k,q,k)
            for role, count in enumerate((q,k)):
                base = layer*(q+k)+(q if role else 0)
                for block, sample in enumerate(samples[base:base+count]):
                    start,end,saw,input_ok,value,actual_block = sample
                    assert start > 0 and end >= start and input_ok == 1
                    assert value == epoch*1024+layer*2+role+1 and actual_block == block
                    assert saw in (0,1) and (block == 0 or saw == 0)
                    total_samples += 1
            root_samples = [samples[layer*(q+k)], samples[layer*(q+k)+q]]
            both = all(sample[2] for sample in root_samples)
            overlap += both
            if mode == 'serial':
                assert not both and root_samples[integer('reverse')][2] == 0
                assert root_samples[1-integer('reverse')][2] == 1
            for position in range(3):
                packet = packets[(3*layer+position)*64:(3*layer+position+1)*64]
                head, setup = struct.unpack_from('<HH',packet)
                kind, ordered = head & 255, (head >> 8) & 1
                acquire, release = (head >> 9) & 3, (head >> 11) & 3
                signal, = struct.unpack_from('<Q',packet,56)
                if position < 2:
                    role = position ^ integer('reverse')
                    assert kind == 2 and ordered == int(position == 0 or mode == 'serial')
                    assert acquire == release == 2 and signal == 0 and setup == 1
                    assert struct.unpack_from('<3H',packet,4) == (128,1,1)
                    assert struct.unpack_from('<3I',packet,12) == ((q if role == 0 else k)*128,1,1)
                    assert struct.unpack_from('<2I',packet,24) == (0,integer('lds'))
                    assert struct.unpack_from('<Q',packet,32)[0] == device['kernel_object']
                    assert struct.unpack_from('<Q',packet,40)[0] != 0
                else:
                    last = layer == layers-1
                    assert kind == 3 and ordered == 1 and acquire == release == (2 if last else 0)
                    assert packet[2:56] == bytes(54) and bool(signal) == last
        assert overlap == integer('overlap_layers')
        key = f'{geometry}/{mode}'
        cell = totals.setdefault(key, dict(trials=0, layers=0, concurrent_layers=0))
        cell['trials'] += 1; cell['layers'] += layers; cell['concurrent_layers'] += overlap
    assert len(queues) == 1 and wraps >= 1
    assert configs == {(r,g,l,o,m) for r in range(4) for g in ('one_block','qk_geometry')
                       for l in (1,8) for o in (0,1) for m in ('serial','parallel')}
    for key, cell in totals.items():
        assert cell['trials'] == 16 and cell['layers'] == 72
        if key.endswith('/serial'): assert cell['concurrent_layers'] == 0
    maps = (out/'maps.txt').read_text()
    assert 'libamdhip64' not in maps
    paths = {line.split()[-1] for line in maps.splitlines() if 'libhsa-runtime64' in line}
    assert len(paths) == 1
    receipt_path = out/'receipt.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        assert receipt['hsa_path'] in paths and receipt['hsa_sha256'] == source['hsa_sha256']
        for name, expected in receipt['files'].items(): assert sha(out/name) == expected, name
    concurrent = all(totals[f'{g}/parallel']['concurrent_layers'] == 72
                     for g in ('one_block','qk_geometry'))
    result = dict(correctness='PASS', capability='PASS' if concurrent else 'FAIL',
                  trials=64, samples=total_samples,
                  publication_wraps=wraps, queue_ids=sorted(queues), cells=totals,
                  actual_overlap=concurrent,
                  interpretation='Long probe capability only; not original Q/K performance or runtime qualification.')
    print(json.dumps(result,indent=2))
    return result

if __name__ == '__main__':
    result = audit(sys.argv[1])
    (Path(sys.argv[1])/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
