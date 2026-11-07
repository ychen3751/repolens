"""Index tracked Python/Markdown files in a local Git checkout without executing code."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from chunking import chunks


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def ingest(root, size=80, overlap=15, syntax=False):
    if not 0 <= overlap < size:
        raise ValueError('Require 0 <= overlap < chunk size')
    root = Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    commit = git(root, 'rev-parse', 'HEAD').decode().strip()
    dirty = bool(git(root, 'status', '--porcelain', '--untracked-files=no').strip())
    records = []
    for raw in git(root, 'ls-files', '-z').split(b'\0'):
        if not raw:
            continue
        name = raw.decode('utf-8')
        path = root / name
        if path.suffix.lower() not in {'.py', '.md'}:
            continue
        if path.is_symlink() or not path.is_file() or root not in path.resolve().parents:
            continue
        if path.stat().st_size > 1_000_000:
            continue
        try:
            content = path.read_bytes()
            text = content.decode('utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        digest = hashlib.sha256(content).hexdigest()
        for chunk in chunks(text, size, overlap, syntax and path.suffix.lower() == '.py'):
            records.append({'path': name, 'base_commit': commit,
                            'working_tree_dirty': dirty, 'file_sha256': digest, **chunk})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument("--syntax", action="store_true", help="Split Python at function boundaries")
    args = parser.parse_args()
    root = Path(git(args.repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    destination = args.output.resolve()
    if destination == root or root in destination.parents:
        parser.error('Output must be outside the source repository to avoid modifying or indexing it')
    rows = ingest(root, syntax=args.syntax)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    print(f'Indexed {len(rows)} chunks from {len({r["path"] for r in rows})} files')


if __name__ == '__main__':
    main()
