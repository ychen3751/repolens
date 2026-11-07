"""Run lexical, semantic and hybrid methods on the same expanded development set."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from importlib.metadata import version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=Path('data/click-syntax.jsonl'))
    parser.add_argument('--dataset', type=Path, default=Path('evaluation/click-dev-expanded.json'))
    parser.add_argument('--output', type=Path, default=Path('evaluation/retrieval-comparison-windowed.json'))
    args = parser.parse_args()
    os.environ.setdefault('HF_HOME', str(Path('data/huggingface').resolve()))
    from huggingface_hub import HfApi
    from semantic import SemanticIndex, HybridIndex
    from search import SearchIndex
    from evaluate import evaluate
    records = [json.loads(s) for s in args.index.read_text().splitlines() if s.strip()]
    dataset = json.loads(args.dataset.read_text())
    config_path = Path('evaluation/embedding-model.json')
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        name = 'sentence-transformers/all-MiniLM-L6-v2'
        config = {'name': name, 'revision': HfApi().model_info(name).sha}
        config_path.write_text(json.dumps(config, indent=2)+'\n')
    queries = [q['question'] for q in dataset['questions']]
    start = time.perf_counter()
    dense = SemanticIndex(records, queries, config['name'], config['revision'], 'data/embeddings')
    preparation = time.perf_counter()-start
    lexical = SearchIndex(records, symbol_context=True)
    report = {'model': config, 'index_sha256': hashlib.sha256(args.index.read_bytes()).hexdigest(),
              'dataset_sha256': hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
              'packages': {p:version(p) for p in ('sentence-transformers','transformers','torch','numpy')},
              'scope':'all files; same corpus and questions for every method',
              'embedding_preparation_seconds':preparation,
              'embedding_policy':'lossless-windows-mean-v1',
              'document_cache_hit':dense.document_cache_hit, 'query_cache_hits':dense.query_cache_hits,
              'embedding_windows':dense.window_count, 'split_chunks':dense.split_chunks,
              'embedding_max_tokens':dense.max_tokens, 'truncated_chunks':dense.truncated,
              'hybrid':{'rrf_constant':60,'candidate_depth_per_method':50}, 'methods':{}}
    for name, retriever in [('bm25',lexical),('semantic',dense),('hybrid',HybridIndex(lexical,dense))]:
        report['methods'][name] = evaluate(records,dataset,symbol_context=True,retriever=retriever)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    for name,result in report['methods'].items():
        print(name, {k:result[k] for k in ('questions','hit_at_1','hit_at_3','hit_at_5','mrr_at_5')})
    print(f'Report saved to {args.output}; truncated chunks: {dense.truncated}')


if __name__ == '__main__':
    main()
