#!/usr/bin/env python3
"""Create a stratified semantic-review packet with full source pages."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

root=Path(__file__).resolve().parents[1]
questions=json.loads((root/"data/questions.json").read_text(encoding="utf-8"))
chapters=json.loads((root/"data/chapters.json").read_text(encoding="utf-8"))
chosen={}
def take(q,reason): chosen.setdefault(q["id"],(q,set()))[1].add(reason)
for chapter in sorted({q["chapter"] for q in questions}): take(next(q for q in questions if q["chapter"]==chapter),"每章至少一題")
for subject in (1,3):
    for typ in ("cloze","mcq","match"):
        q=next((q for q in questions if q["subject"]==subject and q["type"]==typ),None)
        if q: take(q,"每科每題型")
for subject in (1,3):
    pages=[q["physicalPage"] for q in questions if q["subject"]==subject]
    for start in range(1,max(pages)+1,20):
        q=next((q for q in questions if q["subject"]==subject and start<=q["physicalPage"]<start+20),None)
        if q: take(q,"每 20 頁區段")
for page in chapters:
    if page["headerConfidence"]<.8 or page["flags"]:
        q=next((q for q in questions if q["subject"]==page["subject"] and q["physicalPage"]==page["physicalPage"]),None)
        if q: take(q,"低信心或旗標頁")
last=None
for page in chapters:
    key=(page["subject"],page["chapter"])
    if key!=last:
        q=next((q for q in questions if q["subject"]==page["subject"] and q["physicalPage"]==page["physicalPage"]),None)
        if q: take(q,"章節邊界")
        last=key
if len(chosen)<60:
    remaining=[q for q in questions if q["id"] not in chosen]
    step=max(1,len(remaining)//(60-len(chosen)))
    for q in remaining[::step]:
        if len(chosen)>=60: break
        take(q,"全庫等距補樣")
lines=["# 題庫分層抽樣審查包","",f"抽樣 {len(chosen)} 題。這提供語義品質的抽樣信心，不是全庫保證。",""]
for q,reasons in chosen.values():
    text=(root/"data/extracted"/f"s{q['subject']}"/f"p{q['physicalPage']:03}.txt").read_text(encoding="utf-8")
    lines += [f"## {q['id']}","",f"- 原因：{'、'.join(sorted(reasons))}",f"- 題目：{q['prompt']}",f"- 正解：{q['answer']}",f"- 解釋：{q['explanation']}",f"- 出處：{q['chapter']}，{q['page']}（實體頁 {q['physicalPage']}）",f"- whyWrong：{q.get('whyWrong','不適用')}","","```text",text,"```",""]
(root/"data/audit/sample_review.md").write_text("\n".join(lines),encoding="utf-8")
print(f"wrote {len(chosen)} review entries")
