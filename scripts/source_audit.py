#!/usr/bin/env python3
from pathlib import Path
import argparse

IGNORE_DIRS = {".git", "node_modules", "dist", "build", ".next", ".turbo", ".venv", "venv", "__pycache__", ".cache"}
CODE_EXTS = {".ts", ".tsx", ".js", ".jsx", ".py", ".md", ".json", ".yaml", ".yml", ".toml"}
KEYWORDS = ["agent","router","planner","runtime","checkpoint","event","tool","mcp","rag","retriev","embedding","rerank","supabase","rls","tenant","sandpack","playwright","eval","badcase","workflow","approval","schema","sql"]

def ignored(path: Path):
    return any(part in IGNORE_DIRS for part in path.parts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", default=".")
    args = ap.parse_args()
    root = Path(args.repo).resolve()
    files = [p for p in root.rglob("*") if p.is_file() and not ignored(p.relative_to(root))]
    code_files = [p for p in files if p.suffix.lower() in CODE_EXTS]
    keyword_hits = []
    for p in code_files:
        rel = p.relative_to(root)
        low = str(rel).lower()
        if any(k in low for k in KEYWORDS):
            keyword_hits.append(rel)
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")[:5000].lower()
            if any(k in text for k in KEYWORDS):
                keyword_hits.append(rel)
        except Exception:
            pass
    print("# Source Audit Skeleton\n")
    print(f"- repo: {root}")
    print(f"- total files: {len(files)}")
    print(f"- code/config/md files: {len(code_files)}")
    print("\n## AI / Agent keyword hit files")
    for p in keyword_hits[:300]:
        print(f"- {p}")

if __name__ == "__main__":
    main()
