#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
IGNORE = {".git",".obsidian",".opencode",".agents",".codex","scripts","exports","reports","__pycache__"}

def ignored(p): return any(part in IGNORE for part in p.parts)

def main():
    md = [p for p in ROOT.rglob("*.md") if not ignored(p.relative_to(ROOT))]
    empty = []
    for p in md:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if len(text.strip()) < 120 and p.name != "_index.md":
            empty.append(p)
    print("# Vault Audit Report\n")
    print(f"- Markdown files: {len(md)}")
    print(f"- Empty notes: {len(empty)}")
    print("\n## Empty notes")
    for p in empty[:200]:
        print("-", p.relative_to(ROOT))

if __name__ == "__main__":
    main()
