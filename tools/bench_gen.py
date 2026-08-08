#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,random,uuid
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--seed",type=int,default=42);p.add_argument("--events",type=int,choices=(3500,10000),required=True);p.add_argument("--output",type=Path);a=p.parse_args();random.seed(a.seed);base=date(2026,1,1);rows=[]
for i in range(a.events):
    rows.append({"event_id":str(uuid.UUID(int=random.getrandbits(128))),"user_id":"00000000-0000-0000-0000-000000000001","item_id":f"q-bench-{random.randrange(350):03}","study_day":str(base+timedelta(days=random.randrange(180))),"outcome":random.choice(["clean","near","wrong"]),"hint_level":random.randrange(3),"revealed":random.random()<.18,"first_attempt":True,"client_ts":datetime.now(timezone.utc).isoformat()})
out=a.output or Path(f"data/audit/bench-{a.events}.json");out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,separators=(",",":")),encoding="utf-8");print(out)

