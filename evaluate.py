"""Evaluate implementation-span retrieval on a small development set."""
import argparse
import json
from pathlib import Path
from search import SearchIndex


def first_rank(results, evidence):
    for rank, row in enumerate(results, 1):
        if any(row['path'] == e['path'] and row['start_line'] <= e['start_line']
               and row['end_line'] >= e['end_line'] for e in evidence):
            return rank
    return None


def evaluate(records, dataset, source_only=False, source_root="src", symbol_context=False, retriever=None):
    if not records or not dataset['questions']:
        raise ValueError('Index and questions must not be empty')
    if any(r['base_commit'] != dataset['commit'] or r['working_tree_dirty'] for r in records):
        raise ValueError('Evaluation requires clean records at the labeled commit')
    index = retriever if retriever is not None else SearchIndex(records, symbol_context=symbol_context)
    details = []
    for q in dataset['questions']:
        if not q['evidence'] or first_rank(records, q['evidence']) is None:
            raise ValueError(f"No indexed chunk covers evidence for {q['id']}")
        hits = index.search(q['question'], 5, source_only, source_root)
        rank = first_rank(hits, q['evidence'])
        details.append({'id': q['id'], 'question': q['question'], 'rank_at_5': rank,
                        'top_result': {k: hits[0][k] for k in ('path', 'start_line', 'end_line')} if hits else None})
    n = len(details)
    return {'symbol_context': symbol_context, 'search_scope': 'source-only' if source_only else 'all',
            'source_root': source_root if source_only else None,
            'split': dataset['split'], 'label_review': dataset['label_review'],
            'commit': dataset['commit'], 'questions': n,
            'hit_at_1': sum(d['rank_at_5'] == 1 for d in details) / n,
            'hit_at_3': sum(d['rank_at_5'] is not None and d['rank_at_5'] <= 3 for d in details) / n,
            'hit_at_5': sum(d['rank_at_5'] is not None for d in details) / n,
            'mrr_at_5': sum(1/d['rank_at_5'] if d['rank_at_5'] else 0 for d in details) / n,
            'details': details}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=Path('data/click.jsonl'))
    parser.add_argument('--dataset', type=Path, default=Path('evaluation/click-dev.json'))
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--source-root", default="src")
    parser.add_argument("--symbol-context", action="store_true")
    args = parser.parse_args()
    records = [json.loads(s) for s in args.index.read_text().splitlines() if s.strip()]
    print(json.dumps(evaluate(records, json.loads(args.dataset.read_text()), args.source_only, args.source_root, args.symbol_context), indent=2))
