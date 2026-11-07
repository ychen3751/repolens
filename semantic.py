"""Local normalized embeddings and reciprocal-rank fusion for a small corpus."""
import hashlib
import json
from pathlib import Path
from search import SearchIndex


def fuse(rankings, limit=5, constant=60):
    scores, records = {}, {}
    for ranking in rankings:
        seen = set()
        for rank, row in enumerate(ranking, 1):
            key = (row['path'], row['start_line'], row['end_line'])
            if key in seen:
                continue
            seen.add(key)
            records[key] = row
            scores[key] = scores.get(key, 0) + 1 / (constant + rank)
    return [dict(records[k], score=scores[k]) for k in
            sorted(scores, key=lambda k: (-scores[k], k))[:limit]]


def safe_windows(text, tokenizer, max_tokens):
    """Partition text losslessly; validate each part with the actual tokenizer."""
    if len(tokenizer.encode(text, truncation=False, verbose=False)) <= max_tokens:
        return [text]
    if len(text) <= 1:
        raise ValueError('Token limit is too small for this tokenizer')
    middle = len(text) // 2
    # Prefer a nearby line boundary, but guarantee progress on very long lines.
    newline = text.rfind('\n', max(1, middle // 2), middle + 1)
    cut = newline + 1 if newline >= 0 else middle
    return (safe_windows(text[:cut], tokenizer, max_tokens) +
            safe_windows(text[cut:], tokenizer, max_tokens))


def cache_key(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


def save_vectors(path, **values):
    import os
    import tempfile
    import numpy as np
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.npz', delete=False) as f:
        temporary = Path(f.name)
    try:
        np.savez_compressed(temporary, **values)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class SemanticIndex:
    def __init__(self, records, queries, model_name, revision, cache_dir, model_factory=None):
        import numpy as np
        from importlib.metadata import version
        self.records, self.queries = records, queries
        if not records:
            raise ValueError('Cannot embed an empty index')
        texts = [r['path'] + '\n' + r.get('symbol', '') + '\n' + r['text'] for r in records]
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        config = ['lossless-windows-mean-v1', model_name, revision,
                  version('sentence-transformers'), version('transformers')]
        doc_path = cache_dir / ('documents-' + cache_key([config, texts]) + '.npz')
        self.document_cache_hit = doc_path.exists()
        self.query_cache_hits = 0
        self.model = None
        def get_model():
            if self.model is None:
                if model_factory is not None:
                    self.model = model_factory()
                else:
                    from sentence_transformers import SentenceTransformer
                    self.model = SentenceTransformer(model_name, revision=revision,
                                                    device='cpu', trust_remote_code=False)
                if any(getattr(self.model, 'prompts', {}).values()):
                    raise ValueError('Token budgeting currently supports models without prompts only')
            return self.model
        def encode_texts(values, query=False):
            model = get_model()
            groups = [safe_windows(t, model.tokenizer, model.max_seq_length) for t in values]
            flat = [part for group in groups for part in group]
            encoder = model.encode_query if query else model.encode_document
            vectors = encoder(flat, batch_size=32, normalize_embeddings=True,
                              show_progress_bar=not query)
            pooled, cursor = [], 0
            for group in groups:
                # Mean pooling keeps one vector/citation per original source chunk.
                v = np.mean(vectors[cursor:cursor+len(group)], axis=0)
                pooled.append(v / max(float(np.linalg.norm(v)), 1e-12))
                cursor += len(group)
            return np.asarray(pooled), sum(len(g) for g in groups), sum(len(g)>1 for g in groups)
        if self.document_cache_hit:
            with np.load(doc_path, allow_pickle=False) as saved:
                self.documents = saved['vectors']
                self.max_tokens = int(saved['max_tokens'])
                self.window_count = int(saved['window_count'])
                self.split_chunks = int(saved['split_chunks'])
        else:
            self.documents, self.window_count, self.split_chunks = encode_texts(texts)
            self.max_tokens = get_model().max_seq_length
            save_vectors(doc_path, vectors=self.documents, max_tokens=self.max_tokens,
                         window_count=self.window_count, split_chunks=self.split_chunks)
        self.truncated = 0
        vectors = []
        for query in queries:
            path = cache_dir / ('query-' + cache_key([config, query]) + '.npz')
            if path.exists():
                with np.load(path, allow_pickle=False) as saved:
                    vector = saved['vector']
                self.query_cache_hits += 1
            else:
                encoded, _, _ = encode_texts([query], query=True)
                vector = encoded[0]
                save_vectors(path, vector=vector)
            vectors.append(vector)
        self.query_vectors = np.asarray(vectors)
        if (self.documents.ndim != 2 or len(self.documents) != len(records) or
                (queries and self.query_vectors.shape != (len(queries), self.documents.shape[1])) or
                not np.isfinite(self.documents).all() or not np.isfinite(self.query_vectors).all()):
            raise ValueError('Invalid embedding cache shape or values')

    def search(self, query, limit=5, source_only=False, source_root='src'):
        from pathlib import PurePosixPath
        if limit < 1:
            raise ValueError('limit must be positive')
        if not query.strip():
            return []
        vector = self.query_vectors[self.queries.index(query)]
        scores = self.documents @ vector
        candidates = [i for i,r in enumerate(self.records) if not source_only or
                      (PurePosixPath(source_root) in PurePosixPath(r['path']).parents and r['path'].endswith('.py'))]
        candidates.sort(key=lambda i: (-float(scores[i]), self.records[i]['path'], self.records[i]['start_line']))
        return [dict(self.records[i], score=float(scores[i])) for i in candidates[:limit]]


class HybridIndex:
    def __init__(self, lexical, semantic, depth=50):
        self.lexical, self.semantic, self.depth = lexical, semantic, depth

    def search(self, query, limit=5, source_only=False, source_root='src'):
        depth = max(limit, self.depth)
        return fuse([index.search(query, depth, source_only, source_root)
                     for index in (self.lexical, self.semantic)], limit)


if __name__ == '__main__':
    import argparse
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('index', type=Path)
    parser.add_argument('query')
    parser.add_argument('--hybrid', action='store_true')
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    if args.limit < 1 or not args.query.strip():
        parser.error('Provide a nonempty query and positive limit')
    os.environ.setdefault('HF_HOME',str(Path('data/huggingface').resolve()))
    config = json.loads(Path('evaluation/embedding-model.json').read_text())
    records = [json.loads(s) for s in args.index.read_text().splitlines() if s.strip()]
    dense = SemanticIndex(records,[args.query],config['name'],config['revision'],'data/embeddings')
    print(f'Document cache hit: {dense.document_cache_hit}; query cache hits: {dense.query_cache_hits}/{len(dense.queries)}; embedding windows: {dense.window_count}')
    retriever = HybridIndex(SearchIndex(records,symbol_context=True),dense) if args.hybrid else dense
    for rank,row in enumerate(retriever.search(args.query,args.limit),1):
        print(f"\n{rank}. {row['path']}:{row['start_line']}-{row['end_line']} score={row['score']:.4f}")
        print(row['text'])
