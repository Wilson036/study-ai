#!/usr/bin/env python3
"""Generate the fixed offline question bank from the reviewed concept ledger."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def base(c: dict, suffix: str, qtype: str) -> dict:
    ev = c["evidence"][0]
    return {"id": f"q-{c['id'][2:]}-{suffix}", "conceptId": c["id"], "subject": c["subject"], "chapter": c["chapter"],
            "page": ev["page"], "physicalPage": ev["physicalPage"], "type": qtype, "sourceQuote": ev["quote"],
            "difficulty": 2 if c["importance"] >= 2 else 1, "importance": c["importance"], "tombstoned": False}


def learning_clue(c: dict) -> str:
    clue = re.sub(r"[（(][^）)]*[）)]", "", c["gist"]).replace(c["term"], "這個概念")
    clue = re.sub(r"(?:19|20)\d{2}(?:年|年底)?", "", clue)
    clue = re.sub(r"第\s*\d+\s*條", "", clue)
    clue = re.sub(r"\d+(?:\.\d+)?\s*%", "", clue)
    clue = re.sub(r"\s+", "", clue).strip("：:；;，,。．-－◆•")
    return clue or f"{c['chapter']}裡用來解決核心問題的方法"


def make_cloze(c: dict) -> dict:
    item = base(c, "cloze", "cloze")
    term = c["term"]
    clue = learning_clue(c)
    if re.sub(r"\s+", "", term) in re.sub(r"\s+", "", clue):
        clue = f"在{c['chapter']}中用來掌握問題用途與判斷方式的核心觀念"
    prompt = f"教材把「{clue[:46]}」所描述的概念稱為____。"
    item.update({"prompt": prompt, "answer": term, "accept": [term, c["termEn"]] if c["termEn"] else [term],
                 "hints": [f"出現在「{c['chapter']}」", f"第一個字是「{term[0]}」"],
                 "explanation": f"{term}的重點是{clue[:78]}。先抓住它要解決的問題，比背誦完整句子更有用。", "cue": "recall"})
    return item


def make_mcq(c: dict, lookup: dict[str, dict]) -> dict:
    item = base(c, "mcq", "mcq")
    distractors = [lookup[x] for x in c["confusableWith"] if x in lookup][:3]
    if len(distractors) < 3:
        distractors += [x for x in lookup.values() if x["chapter"] == c["chapter"] and x["id"] != c["id"] and x not in distractors][:3-len(distractors)]
    choices = [c["term"]] + [x["term"] for x in distractors]
    # deterministic rotation prevents the correct choice always being first.
    shift = sum(ord(ch) for ch in c["id"]) % len(choices)
    choices = choices[shift:] + choices[:shift]
    answer_index = choices.index(c["term"])
    wrong = {x["term"]: f"{x['term']}著重於{x['gist'][:34]}，和題幹描述的焦點不同。" for x in distractors}
    clue = learning_clue(c)
    item.update({"prompt": f"哪個概念最符合這段用途：{clue[:58]}？", "answer": c["term"], "choices": choices,
                 "answerIndex": answer_index, "whyWrong": [wrong[x] for x in choices if x != c["term"]],
                 "explanation": f"題幹聚焦在{clue[:68]}，因此答案是{c['term']}。", "cue": "discrimination"})
    return item


def make_match(c: dict) -> dict:
    item = base(c, "match", "match")
    clue = learning_clue(c)
    item.update({"prompt": f"請替「{c['term']}」找出最貼近的核心意思。", "left": c["term"], "right": clue[:56], "answer": c["term"],
                 "groupHint": c["chapter"], "explanation": f"{c['term']}可用一句話記成：{c['gist'][:68]}。", "cue": "application"})
    return item


def generate(root: Path, total: int) -> list[dict]:
    concepts = json.loads((root / "data/concepts.json").read_text(encoding="utf-8"))
    lookup = {x["id"]: x for x in concepts}
    questions = [make_cloze(c) for c in concepts]
    second_needed = max(0, total - len(questions))
    for i, c in enumerate(concepts[:second_needed]):
        questions.append(make_match(c) if i < 48 else make_mcq(c, lookup))
    questions.sort(key=lambda x: (x["subject"], x["chapter"], x["conceptId"], x["type"]))
    (root / "data/questions.json").write_text(json.dumps(questions, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return questions


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--total", type=int, default=300)
    args = p.parse_args()
    result = generate(args.root, args.total)
    print(f"generated {len(result)} questions")
