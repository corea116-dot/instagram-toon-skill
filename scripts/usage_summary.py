#!/usr/bin/env python3
"""Aggregate explicitly supplied run logs once per response ID; never infer price."""
import argparse
import json
from collections import Counter
from pathlib import Path

def summarize(paths, since, until):
    total=Counter();roles=[];seen=set()
    for path in paths:
        usage=Counter();count=0;models=set()
        for line in path.open():
            record=json.loads(line);stamp=record.get('timestamp','');p=record.get('payload',{})
            if stamp < since or stamp > until:continue
            if record['type']=='turn_context':models.add((p.get('model'),p.get('effort')))
            if record['type']!='token_usage_record':continue
            key=p.get('response_id')
            if not key or key in seen:continue
            seen.add(key);usage.update(p['usage']);count+=1
        total.update(usage)
        roles.append({'log':str(path),'responses':count,'usage':dict(usage),
                      'observed_models':[{'model':a,'effort':b} for a,b in sorted(models)]})
    return {'since':since,'through':until,'responses':len(seen),'usage':dict(total),
            'uncached_input_tokens':total['input_tokens']-total['cached_input_tokens'],
            'logs':roles,'currency_cost':None,
            'limitations':'Only supplied logs and completed response records in the interval. Image-provider internal usage and unsupplied automatic review logs excluded. Cached input/reasoning already included in input/output.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--since',required=True);p.add_argument('--until',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('logs',nargs='+',type=Path)
    a=p.parse_args();a.output.write_text(json.dumps(summarize(a.logs,a.since,a.until),ensure_ascii=False,indent=2)+'\n');print(a.output)
