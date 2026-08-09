#!/usr/bin/env python3
"""Build the deployable shell and immutable bank manifest."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


def build(root: Path) -> None:
    src, dist, data = root / "src", root / "dist", root / "data"
    if dist.exists(): shutil.rmtree(dist)
    dist.mkdir()
    for name in ("index.html", "config.js", "sw.js", "_headers"):
        shutil.copy2(src / name, dist / name)
    bank = (data / "questions.json").read_bytes()
    concept_bank = (data / "concepts.json").read_bytes()
    questions = json.loads(bank)
    concepts = json.loads(concept_bank)
    manifest={
        "bankVersion": 2,
        "schemaVersion": 2,
        "sha256": hashlib.sha256(bank).hexdigest(),
        "itemCount": len(questions),
        "bytes": len(bank),
        "conceptSha256": hashlib.sha256(concept_bank).hexdigest(),
        "conceptCount": len(concepts),
        "conceptBytes": len(concept_bank),
    }
    (data / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    html=(dist/"index.html").read_bytes()
    if len(html)>500*1024: raise SystemExit("dist/index.html 超過 500 KB")
    if len(gzip.compress(html))>150*1024: raise SystemExit("dist/index.html gzip 超過 150 KB")
    if len(bank)>1.5*1024*1024: raise SystemExit("questions.json 超過 1.5 MB")
    if len(concept_bank)>1.5*1024*1024: raise SystemExit("concepts.json 超過 1.5 MB")
    print(f"index.html: {len(html)} bytes, gzip {len(gzip.compress(html))} bytes")
    print(f"questions.json: {len(bank)} bytes, sha256 {manifest['sha256']}")
    print(f"concepts.json: {len(concept_bank)} bytes, sha256 {manifest['conceptSha256']}")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);build(p.parse_args().root)
