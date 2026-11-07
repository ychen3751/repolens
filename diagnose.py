"""Inspect development misses without changing retrieval or relevance labels."""
import json
from pathlib import Path
from evaluate import first_rank
from search import SearchIndex, tokenize


def diagnose(records, dataset):
    if any(r['base_commit'] != dataset['commit'] or r['working_tree_dirty'] for r in records):
        raise ValueError('Index must match the clean labeled commit')
    index = SearchIndex(records)
    report = []
    for q in dataset['questions']:
        results = index.search(q['question'], max(1, len(records)), source_only=True)
        rank = first_rank(results, q['evidence'])
        if rank is not None and rank <= 5:
            continue
        terms = set(tokenize(q['question']))
        def summarize(row):
            tokens = set(tokenize(row['path'] + ' ' + row['text']))
            return {**{k: row[k] for k in ('path', 'start_line', 'end_line', 'score')},
                    'matched_query_terms': sorted(terms & tokens),
                    'missing_query_terms': sorted(terms - tokens)}
        report.append({'id': q['id'], 'question': q['question'], 'evidence': q['evidence'],
                       'first_evidence_rank': rank,
                       'target_chunk': summarize(results[rank-1]) if rank else None,
                       'top_five': [summarize(r) for r in results[:5]]})
    return report


if __name__ == '__main__':
    records = [json.loads(s) for s in Path('data/click.jsonl').read_text().splitlines() if s.strip()]
    dataset = json.loads(Path('evaluation/click-dev.json').read_text())
    print(json.dumps(diagnose(records, dataset), indent=2))
