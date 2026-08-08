#!/usr/bin/env python3
"""Extract the two study guides page-by-page and build a chapter manifest."""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

PDF_NAMES = {
    1: "AI應用規劃師(中級)-學習指引-科目1人工智慧技術應用規劃_20251222101833.pdf",
    3: "AI應用規劃師(中級)-學習指引-科目3機器學習技術與應用_20251222101907.pdf",
}
HEADER_RE = re.compile(r"第([一二三四五六七八九十]+)章\s*([^\n]{1,32}?)\s+(\d+[-–]\d+)")
PRINT_RE = re.compile(r"(?<!\d)(\d+[-–]\d+)(?!\d)")


def clean_text(text: str) -> str:
    text = text.replace("\uf07d", "").replace("\uf077", "•").replace("\uf0a1", "•").replace("\uf097", "◆")
    text = text.replace("\u00a0", " ").replace("–", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def page_meta(text: str, previous_chapter: str | None) -> tuple[str | None, str | None, float, list[str]]:
    first = " ".join(text.splitlines()[:4])
    header = HEADER_RE.search(first)
    printed = PRINT_RE.search(first)
    chapter = previous_chapter
    confidence = 0.35
    if header:
        chapter = f"第{header.group(1)}章 {header.group(2).strip()}"
        printed_page = header.group(3).replace("–", "-")
        confidence = 1.0
    else:
        printed_page = printed.group(1).replace("–", "-") if printed else None
        confidence = 0.82 if printed_page and chapter else (0.55 if chapter else 0.2)
    flags: list[str] = []
    compact = re.sub(r"\s", "", text)
    if len(compact) < 150:
        flags.append("short_page")
    digit_sep = len(re.findall(r"[\d|｜:：,，;；]", text)) / max(len(text), 1)
    if digit_sep > 0.12 or (text.count("\n") > 20 and digit_sep > 0.07):
        flags.append("table_like")
    if "目錄" in first or len(re.findall(r"\d+-\d+", text)) > 12:
        flags.append("toc")
    if re.search(r"參考(文獻|資料)", first):
        flags.append("reference")
    if printed_page and chapter and printed_page.split("-")[0] not in chinese_chapter_number(chapter):
        flags.append("header_mismatch")
        confidence = min(confidence, 0.7)
    return chapter, printed_page, confidence, flags


def chinese_chapter_number(chapter: str) -> set[str]:
    chars = re.search(r"第([一二三四五六七八九十]+)章", chapter)
    table = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    return {str(table.get(chars.group(1), 0))} if chars else set()


def extract(root: Path) -> list[dict]:
    data = root / "data"
    extracted = data / "extracted"
    audit = data / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for subject, filename in PDF_NAMES.items():
        pdf = root.parent / filename
        if not pdf.exists():
            raise SystemExit(f"找不到教材：{pdf}")
        out = extracted / f"s{subject}"
        out.mkdir(parents=True, exist_ok=True)
        reader = PdfReader(pdf)
        chapter = None
        for index, page in enumerate(reader.pages, 1):
            text = clean_text(page.extract_text() or "")
            (out / f"p{index:03}.txt").write_text(text, encoding="utf-8")
            chapter, printed, confidence, flags = page_meta(text, chapter)
            excluded = bool(chapter and chapter.startswith("第一章")) or any(f in flags for f in ("toc", "reference", "table_like")) or confidence < 0.8
            rows.append({
                "subject": subject, "physicalPage": index, "printedPage": printed,
                "chapter": chapter or "未辨識章節", "headerConfidence": confidence,
                "flags": flags, "excludedFromGeneration": excluded,
            })
    (data / "chapters.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(rows, audit / "extract_report.md")
    return rows


def write_report(rows: list[dict], target: Path) -> None:
    low = [r for r in rows if r["headerConfidence"] < 0.8]
    flags = Counter(f for r in rows for f in r["flags"])
    boundaries = []
    last = None
    for r in rows:
        key = (r["subject"], r["chapter"])
        if key != last:
            boundaries.append(r)
            last = key
    lines = [
        "# 抽取稽核報告", "", f"- 總頁數：{len(rows)}", f"- 平均標頭信心：{statistics.mean(r['headerConfidence'] for r in rows):.2f}",
        f"- 低信心頁：{len(low)}", f"- 排除出題頁：{sum(r['excludedFromGeneration'] for r in rows)}", "",
        "## Flags", "", *(f"- `{k}`：{v}" for k, v in sorted(flags.items())), "", "## 章節邊界", "",
        *(f"- 科目 {r['subject']} 實體第 {r['physicalPage']} 頁：{r['chapter']}（{r['printedPage'] or '無印刷頁碼'}）" for r in boundaries),
        "", "## 低信心頁", "", *(f"- s{r['subject']}/p{r['physicalPage']:03}：{r['flags']}" for r in low), "",
        "> 印刷頁碼、章節與低信心頁需在分層抽樣時人工核對；本報告不宣稱語義正確。", "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = extract(args.root)
    print(f"extracted {len(result)} pages")

