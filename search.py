"""Small BM25 keyword baseline. Scores are relevance scores, not confidence."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path, PurePosixPath
import re

STOP = set('a an the is are how where what does do to in of for and can i it this'.split())


def tokenize(text):
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    return [t for t in re.findall(r'[a-z0-9]+', text.lower()) if t not in STOP]


class SearchIndex:
    def __init__(self, records, symbol_context=False):
        self.records = records
        self.counts = [Counter(tokenize(r['path'] + ' ' + r['text'] + (' ' + r.get('symbol', '') if symbol_context else ''))) for r in records]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.average = sum(self.lengths) / max(len(records), 1) or 1
        self.frequency = Counter(t for c in self.counts for t in c)

    def search(self, query, limit=5, source_only=False, source_root="src"):
        root = PurePosixPath(source_root)
        if source_only and (root.is_absolute() or ".." in root.parts or not root.parts):
            raise ValueError("source_root must be a nonempty relative directory")
        if limit < 1:
            raise ValueError('limit must be positive')
        results = []
        for row, counts, length in zip(self.records, self.counts, self.lengths):
            path = PurePosixPath(row["path"])
            if source_only and (root not in path.parents or path.suffix != ".py"):
                continue
            score = 0.0
            for term in set(tokenize(query)):
                tf = counts[term]
                if not tf:
                    continue
                df = self.frequency[term]
                idf = math.log(1 + (len(self.records) - df + 0.5) / (df + 0.5))
                score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * length / self.average))
            if score > 0:
                results.append(dict(row, score=score))
        return sorted(results, key=lambda r: (-r['score'], r['path'], r['start_line']))[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('index', type=Path)
    parser.add_argument('query')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument("--source-only", action="store_true", help="Search only Python files under --source-root")
    parser.add_argument("--source-root", default="src", help="Repository-relative implementation directory")
    parser.add_argument("--symbol-context", action="store_true", help="Include stored class/function names in BM25 text")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    rows = [json.loads(line) for line in args.index.read_text(encoding='utf-8').splitlines() if line.strip()]
    results = SearchIndex(rows, symbol_context=args.symbol_context).search(args.query, args.limit, args.source_only, args.source_root)
    if not results:
        print('No keyword matches. This does not prove the repository lacks an answer.')
    for rank, row in enumerate(results, 1):
        print(f"\n{rank}. {row['path']}:{row['start_line']}-{row['end_line']}  BM25={row['score']:.3f}")
        print(f"Base commit: {row['base_commit']} | dirty: {row['working_tree_dirty']}")
        print(row['text'])


if __name__ == '__main__':
    main()
