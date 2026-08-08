#!/usr/bin/env python3
"""Deterministically mine a reviewable core-concept ledger from extracted pages."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

TERM_PATTERNS = [
    re.compile(r"(?:^|[◆•，。、；：:\n])\s*([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9 －-]{1,16})\s*[（(]([A-Za-z][A-Za-z0-9 /-]{1,45})[）)]\s*[：:]?", re.M),
    re.compile(r"(?:^|[◆•\n])\s*([\u4e00-\u9fff]{2,12})[：:]", re.M),
    re.compile(r"(?:^|[。；\n])\s*([\u4e00-\u9fff]{2,12})是指", re.M),
]
NOISE_WORDS = {
    "例如","包括","以及","其中","使用","透過","資料","模型","方法","技術","系統","企業","組織","能力","步驟","目的","原理","特點","應用場景",
    "定義","優點","缺點","限制","示例","範例","例子","實例","案例說明","補充說明","說明","功能","內容","結論","風險","問題","流程","處理流程",
    "適用情境","適用場景","比較對象","主要職責","能力需求","其主要目標包括","不同等級可分為","代表技術與模型","常見演算法如下","常用統計方法包括",
    "計算公式是","學習","理解","生成","重大","地名","自由性","分類任務",
    "災難性","森林","解析","案例","應用","目標","公式","過程","意義","橫軸","分子","分母","判別","適用","挑戰","優勢","用途","影響","發生原因","情況特徵","常見情境","常見問題","常用模型","參數說明","幾何意義","觀察結果","技術基礎","目標描述","公式示意","運作原理","運作方式","常見類型","適用範圍","衡量標準","品質控制","應用情境","處理機制","移除",
    "醫療診斷","金融風控","郵件分類","圖像辨識","銷售量預測","房價預測","案例說明","技術門檻低","靈活性","彈性有限","任務效果優異","快速部署",
    "核心技術概念","任務類型與建議模型","分類任務中的條件預測","生成模型中的變數關聯建構","影響案例","機器學習方法","統計方法","評估方式","處理策略","技術效能",
    "詞序列","深度學習模型",
}
BAD_TERM = re.compile(r"(?:如下|包括|標注為|構成了|主要目標|不同等級|代表技術|能力強|表現較差|無法|解決的痛點|階段限制|高模型效能|降低技術門檻|適應不同|是否|這類|其中|用於|公式是|為目標變數|誤用於|效果優異|高度依賴|成本高|敏感|有限|過高|過低|不足|不當|不連續|是)$")
BAD_PREFIX = re.compile(r"^(?:也構成|轉而|通過|若|其功能|此公式|達到|需透過|成效|例如|直接以|資料量|決策邊界|控情境|對輸入|在分類|這個過程|採用了|像在告訴|其中層|並通過|通常使用|用絕對值|作用於|透過遞歸|和條件|將圖像|可設計|模型表現|採用了與|話系統|對角元素|基於雙向|入自然語言處理|豐富語意|模型硬體|技術的比較|術的比較|無法|利於|提升|強化|穩定|適應)")


def compact(s: str) -> str:
    s = re.sub(r"\s+", "", s).strip("：:；;，,。．-－◆•")
    s = re.sub(r"^(?:不論是在|論是在|隨著|到近年|以及|而|與|及|或稱|或|也稱為|又稱為|稱為|稱|也構成了|轉而採用了|的)+", "", s)
    return s


def slug(term: str) -> str:
    latin = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")
    return latin[:34] if latin else hashlib.sha1(term.encode()).hexdigest()[:12]


def sentence_around(text: str, start: int, term: str) -> str:
    left = max(text.rfind("。", 0, start), text.rfind("\n", 0, start)) + 1
    ends = [x for x in (text.find("。", start), text.find("\n", start)) if x >= 0]
    right = min(ends) + 1 if ends else min(len(text), start + 120)
    quote = text[left:right].strip()
    if len(quote) < 18:
        quote = text[start:start + 120].strip()
    return quote[:60].strip()


def gist_around(text: str, start: int, raw_term: str, term: str, term_en: str) -> str:
    context = text[start:start + 220]
    context = re.split(r"\n\s*◆", context, 1)[0]
    context = re.sub(r"\s+", "", context)
    context = context.replace(re.sub(r"\s+", "", raw_term), "", 1)
    context = context.replace(term, "", 1)
    if term_en:
        compact_en = re.sub(r"\s+", "", term_en)
        context = re.sub(rf"[（(]{re.escape(compact_en)}[）)]", "", context, count=1, flags=re.I)
    context = context.lstrip("◆•○：:是指為,，、-－")
    if "•" in context:
        context = context.split("•", 1)[0]
    if "。" in context and context.index("。") >= 12:
        context = context.split("。", 1)[0]
    return context[:76].rstrip("◆•：:，,。；;")


def build(root: Path, target_count: int) -> list[dict]:
    manifest = json.loads((root / "data/chapters.json").read_text(encoding="utf-8"))
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for page in manifest:
        if page["excludedFromGeneration"] or not page["printedPage"]:
            continue
        text_path = root / "data/extracted" / f"s{page['subject']}" / f"p{page['physicalPage']:03}.txt"
        text = text_path.read_text(encoding="utf-8")
        for pattern in TERM_PATTERNS:
            for match in pattern.finditer(text):
                raw_term = match.group(1)
                term = compact(raw_term)
                if not 2 <= len(term) <= 12 or term in NOISE_WORDS or BAD_TERM.search(term) or BAD_PREFIX.search(term) or re.search(r"\d", term) or re.match(r"^[A-Za-z].*[\u4e00-\u9fff]", term) or term.endswith(("的","與","和","為")):
                    continue
                key = (page["chapter"], term.lower())
                if key in seen:
                    continue
                quote = sentence_around(text, match.start(), term)
                if term not in compact(quote) or len(quote) < 15:
                    continue
                seen.add(key)
                term_en = match.group(2).strip() if match.lastindex and match.lastindex >= 2 else ""
                gist = gist_around(text, match.start(1), raw_term, term, term_en)
                if len(gist) < 12 or "Ans" in gist or "S=" in gist or gist.startswith(("教材中","出現在","與","和","或","的","則","還是","再到","、","，","。","—")):
                    continue
                unique_slug = f"{slug(term)}-{hashlib.sha1((page['chapter'] + term).encode()).hexdigest()[:6]}"
                candidates.append({
                    "id": f"c-s{page['subject']}-{unique_slug}", "subject": page["subject"], "chapter": page["chapter"],
                    "term": term, "termEn": term_en, "gist": gist, "importance": 3 if len(candidates) % 5 == 0 else 2,
                    "confusableWith": [], "evidence": [{"page": page["printedPage"], "physicalPage": page["physicalPage"], "quote": quote}],
                    "allowedTypes": ["cloze", "mcq", "match"],
                })
    # Balance subjects and chapters before filling remaining slots.
    chosen: list[dict] = []
    chapter_quotes: dict[str, list[set[str]]] = {}
    chapter_terms: dict[str, list[str]] = {}
    buckets: dict[tuple[int, str], list[dict]] = {}
    for item in candidates:
        buckets.setdefault((item["subject"], item["chapter"]), []).append(item)
    while len(chosen) < target_count and any(buckets.values()):
        for key in sorted(buckets):
            while buckets[key] and len(chosen) < target_count:
                candidate = buckets[key].pop(0)
                existing_terms = chapter_terms.setdefault(candidate["chapter"], [])
                if any(candidate["term"] in old or old in candidate["term"] for old in existing_terms):
                    continue
                normalized = re.sub(r"\s+", "", candidate["evidence"][0]["quote"])
                grams = {normalized[i:i+5] for i in range(max(1, len(normalized)-4))}
                existing = chapter_quotes.setdefault(candidate["chapter"], [])
                if any(len(grams & old) / max(1, len(grams | old)) > .68 for old in existing):
                    continue
                chosen.append(candidate)
                existing.append(grams)
                existing_terms.append(candidate["term"])
                break
    by_chapter: dict[str, list[dict]] = {}
    for item in chosen:
        by_chapter.setdefault(item["chapter"], []).append(item)
    for items in by_chapter.values():
        for i, item in enumerate(items):
            item["confusableWith"] = [x["id"] for x in items if x["id"] != item["id"]][:3]
    (root / "data/concepts.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")
    return chosen


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--count", type=int, default=175)
    args = p.parse_args()
    concepts = build(args.root, args.count)
    print(f"generated {len(concepts)} concepts")
