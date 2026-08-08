#!/usr/bin/env python3
"""Hard validation gates for the fixed question bank."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ID_RE = re.compile(r"^q-s[13]-[a-z0-9-]+-(cloze|mcq|match)$")
BANNED = re.compile(r"(?:以上皆[非是]|\bL\d{5}\b|\b(?:19|20)\d{2}\b|\d+(?:\.\d+)?\s*%|第\s*\d+\s*條)", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def ngrams(s: str, n: int = 5) -> set[str]:
    s = norm(s)
    return {s[i:i+n] for i in range(max(0, len(s)-n+1))}


def validate(root: Path, incremental: bool = False) -> tuple[list[str], list[str]]:
    questions = json.loads((root / "data/questions.json").read_text(encoding="utf-8"))
    concepts = json.loads((root / "data/concepts.json").read_text(encoding="utf-8"))
    concept_by_id = {x["id"]: x for x in concepts}
    errors: list[str] = []
    warnings: list[str] = []
    ids = [q.get("id") for q in questions]
    if len(ids) != len(set(ids)): errors.append("question id 不唯一")
    if not incremental and not 250 <= len(questions) <= 350: errors.append(f"題數 {len(questions)} 不在 250–350")
    chapter_counts = Counter(q.get("chapter") for q in questions)
    for chapter, count in chapter_counts.items():
        if count < 3: errors.append(f"{chapter} 只有 {count} 題")
    type_counts = Counter(q.get("type") for q in questions)
    targets = {"cloze": .50, "mcq": .32, "match": .18}
    for typ, target in targets.items():
        actual = type_counts[typ] / max(1, len(questions))
        if abs(actual-target)/target > .20: warnings.append(f"{typ} 比例 {actual:.1%} 超出軟目標相對 ±20%")
    per_concept: dict[str, list[dict]] = defaultdict(list)
    chapter_prompts: dict[str, list[dict]] = defaultdict(list)
    match_seen: dict[str, tuple[set, set]] = defaultdict(lambda: (set(), set()))
    for q in questions:
        qid = q.get("id", "")
        if not ID_RE.match(qid): errors.append(f"{qid}: id 命名不合法")
        c = concept_by_id.get(q.get("conceptId"))
        if not c: errors.append(f"{qid}: conceptId 不存在"); continue
        per_concept[q["conceptId"]].append(q); chapter_prompts[q["chapter"]].append(q)
        if q.get("subject") != c["subject"] or q.get("chapter") != c["chapter"]: errors.append(f"{qid}: 科目或章節與概念不符")
        for field in ("prompt", "answer", "explanation", "sourceQuote"):
            if not isinstance(q.get(field), str) or not q[field].strip(): errors.append(f"{qid}: 缺少 {field}")
        if not 15 <= len(q.get("explanation", "")) <= 120: errors.append(f"{qid}: explanation 長度不符")
        if len(q.get("sourceQuote", "")) > 60: errors.append(f"{qid}: sourceQuote 超過 60 字")
        page_file = root / "data/extracted" / f"s{q['subject']}" / f"p{q['physicalPage']:03}.txt"
        if not page_file.exists() or q.get("sourceQuote") not in page_file.read_text(encoding="utf-8"): errors.append(f"{qid}: sourceQuote 不是頁面原文子字串")
        scanned = json.dumps({k:q.get(k) for k in ("prompt","answer","choices")}, ensure_ascii=False)
        if BANNED.search(scanned): errors.append(f"{qid}: 命中禁挖清單")
        if q["type"] == "cloze":
            if "____" not in q["prompt"]: errors.append(f"{qid}: 填空缺少 ____")
            answer = q["answer"]
            if (re.search(r"[\u4e00-\u9fff]", answer) and len(answer) > 12) or (answer.isascii() and len(answer.split()) > 3): errors.append(f"{qid}: 填空答案過長")
            if norm(answer) in norm(q["prompt"]): errors.append(f"{qid}: 答案出現在 prompt")
            if not 1 <= len(q.get("hints", [])) <= 3: errors.append(f"{qid}: hints 數量不符")
            if any(norm(answer) in norm(h) for h in q.get("hints", [])): errors.append(f"{qid}: 提示直接洩答")
        elif q["type"] == "mcq":
            choices = q.get("choices", [])
            if not 3 <= len(choices) <= 4 or len(set(choices)) != len(choices): errors.append(f"{qid}: choices 不合法")
            if not 0 <= q.get("answerIndex", -1) < len(choices) or choices[q["answerIndex"]] != q["answer"]: errors.append(f"{qid}: answerIndex 不合法")
            allowed = {concept_by_id[x]["term"] for x in c.get("confusableWith", []) if x in concept_by_id}
            if any(x != q["answer"] and x not in allowed for x in choices): errors.append(f"{qid}: 誘答項不在 confusableWith")
            if len(q.get("whyWrong", [])) != len(choices)-1: errors.append(f"{qid}: whyWrong 數量不符")
        elif q["type"] == "match":
            lefts, rights = match_seen[q.get("groupHint", "")]
            if q.get("left") in lefts or q.get("right") in rights: errors.append(f"{qid}: 配對群組內重複")
            lefts.add(q.get("left")); rights.add(q.get("right"))
        else: errors.append(f"{qid}: 未知題型")
    for cid, items in per_concept.items():
        if len(items) > 2: errors.append(f"{cid}: 超過兩題")
        if len(items) == 2 and (items[0]["type"] == items[1]["type"] or items[1].get("cue") not in ("application","discrimination")): errors.append(f"{cid}: 第二題題型或 cue 不符")
    for chapter, items in chapter_prompts.items():
        for i, a in enumerate(items):
            ga=ngrams(a["prompt"])
            for b in items[i+1:]:
                gb=ngrams(b["prompt"])
                score=len(ga&gb)/max(1,len(ga|gb))
                if score>.8: errors.append(f"{a['id']} / {b['id']}: prompt n-gram 重複 {score:.2f}")
    return errors, warnings


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument("--incremental",action="store_true");args=p.parse_args()
    errors,warnings=validate(args.root,args.incremental)
    for x in warnings: print(f"WARNING: {x}")
    for x in errors: print(f"ERROR: {x}")
    print(f"validation: {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(bool(errors))

