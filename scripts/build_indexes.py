#!/usr/bin/env python3
from pathlib import Path
import re
ROOT=Path.cwd(); IGN={'.git','.obsidian','.opencode','.codex','skills','scripts','exports','reports','__pycache__'}
def main():
    changed=[]
    for d in ROOT.iterdir():
        if not d.is_dir() or d.name in IGN or d.name.startswith('.'): continue
        if not (re.match(r'^\d{2}-',d.name) or d.name.startswith('00-') or '项目案例' in d.name or '源码证据' in d.name): continue
        notes=sorted([p for p in d.glob('*.md') if p.name!='_index.md'], key=lambda p:p.name)
        if not notes: continue
        idx=d/'_index.md'; old=idx.read_text(encoding='utf-8',errors='ignore') if idx.exists() else ''
        block='## 自动索引\n'+'\n'.join(f'- [[{p.stem}]]' for p in notes)+'\n'
        new=(f'# {d.name}\n\n'+block) if not old.strip() else old.rstrip()+'\n\n'+block
        idx.write_text(new, encoding='utf-8'); changed.append(idx.relative_to(ROOT))
    print('# Index Build Report\n'+'\n'.join(f'- updated: {p}' for p in changed) if changed else '# Index Build Report\n- no changes')
if __name__=='__main__': main()
