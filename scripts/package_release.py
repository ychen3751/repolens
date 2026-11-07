"""Create an allowlisted source archive; never includes data, credentials, or environments."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TOP={'.gitignore','.env.example','README.md','THIRD_PARTY_NOTICES.md','requirements-semantic.lock.txt'}
DIRS={'tests','docs','evaluation','scripts'}


def files():
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or p.is_symlink(): continue
        rel=p.relative_to(ROOT)
        if any(part in {'__pycache__','.venv','data','.git','dist','build'} for part in rel.parts): continue
        if len(rel.parts)==1:
            allowed=rel.name in TOP or rel.suffix=='.py'
        else:
            allowed=rel.parts[0] in DIRS and rel.suffix in {'.py','.md','.json'}
        if allowed: yield p,rel


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/repolens-source.zip')
    a=parser.parse_args()
    selected=list(files())
    findings=[]
    patterns=[r'\bsk-[A-Za-z0-9_-]{20,}',r'\bgh[pousr]_[A-Za-z0-9]{20,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    for path,rel in selected:
        text=path.read_text(encoding='utf-8')
        if any(re.search(pattern,text) for pattern in patterns): findings.append(str(rel))
    if findings:
        raise SystemExit('Potential secret patterns found in files (values suppressed): '+', '.join(findings))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    manifest=[]
    with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED) as z:
        for path,rel in selected:
            content=path.read_bytes()
            z.writestr('repolens/'+rel.as_posix(),content)
            manifest.append({'path':rel.as_posix(),'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    manifest_path=a.output.with_suffix('.manifest.json')
    manifest_path.write_text(json.dumps({'files':manifest,'secret_scan':'Limited pattern scan only; not a guarantee of no secrets.'},indent=2)+'\n')
    print(f'Packaged {len(manifest)} files: {a.output}')
    print(f'Manifest: {manifest_path}')


if __name__=='__main__': main()
