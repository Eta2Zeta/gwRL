"""Validate exported campaign evidence and reconstruct every unit-board delta.

The generator performs authoritative Engine replay. This verifies the saved
record's consistency; --current additionally checks recorded runtime-source SHA.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def verify(path, current=False):
    data=json.loads(Path(path).read_text())
    assert data['schema_version']==2
    assert data['terminal'] and data['exact_replay_verified']
    assert data['national_turns']==44
    assert data['final_snapshot']['completed_turns']==dict.fromkeys(['ccp','mongolia','japan','kmt'],11)
    clock=data['final_snapshot']['clock']
    assert (clock['year'],clock['month'],clock['round'],clock['serial'])==(1941,7,10,'44')
    initial=json.loads(data['initial_checkpoint'])['state']
    final=json.loads(data['final_checkpoint'])['state']
    assert len(initial['units'])==99 and initial['clock']['player_turn_serial']=='0'
    assert not initial['history'] and not json.loads(data['initial_checkpoint'])['random']['test_tape']
    assert data['invariant_checks']==len(data['transitions'])+1
    units=deepcopy(data['initial_snapshot']['units']);seen=set(units)
    land=deepcopy(data['initial_snapshot']['territories']);cash=deepcopy(data['initial_snapshot']['treasuries'])
    events=[];actions=Counter();kinds=Counter()
    for number,step in enumerate(data['transitions']):
        assert step['index']==number and step['invariants']=='passed'
        for unit in step['unit_destruction']:
            assert units.pop(unit['id'])==unit
        for unit in step['unit_creation']:
            assert unit['id'] not in seen
            seen.add(unit['id']);units[unit['id']]=unit
        for unit in step['unit_updates']:
            assert unit['id'] in units
            units[unit['id']]=unit
        land.update(step['possession_changes']);cash.update(step['treasury_changes'])
        assert land==step['snapshot']['territories'] and cash==step['snapshot']['treasuries']
        inputs=[event for event in step['events'] if event['kind'] in ('action','chance','interrupt')]
        assert len(inputs)==1 and inputs[0]['kind']==step['kind']
        if step['kind']=='chance':assert inputs[0]['payload']['request_id']==step['input']['request_id']
        else:
            assert inputs[0]['payload']==step['input'];actions[step['input']['kind']]+=1
        assert inputs[0]['after_state_key']==step['state_key']
        events.extend(step['events']);kinds[step['kind']]+=1
    assert units==data['final_snapshot']['units']
    assert events==final['history']
    assert dict(actions)==data['action_counts']
    assert kinds['chance']==data['chance_transitions']
    assert kinds['action']+kinds['interrupt']==data['action_transitions']
    for unit in final['units'].values():
        exported=units[unit['id']]
        for source,target in [('id','id'),('type','type'),('owner','owner'),('zone','zone'),('damage','damage'),('movement_remaining','movement'),('carried_by','carried_by'),('cargo','cargo')]:
            assert unit[source]==exported[target]
    if current:
        for file,digest in data['runtime_source_sha256'].items():
            assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==digest, f'Runtime source changed: {file}'
    return {'path':str(path),'transitions':len(data['transitions']),'national_turns':44,'action_counts':dict(actions),'chance_transitions':kinds['chance'],'definition_fingerprint':data['definition_fingerprint'],'trace_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('paths',nargs='+');parser.add_argument('--current',action='store_true');args=parser.parse_args()
    for path in args.paths:print(json.dumps(verify(path,args.current),sort_keys=True))
