"""Explicit candidate scopes; no automatic query intent classification."""
from pathlib import PurePosixPath


class ScopedIndex:
    def __init__(self, index, records, scope='all', docs_root='docs'):
        root=PurePosixPath(docs_root)
        if scope not in ('all','guide') or root.is_absolute() or '..' in root.parts or not root.parts:
            raise ValueError('Invalid scope or documentation directory')
        self.index,self.records,self.scope,self.root=index,records,scope,root

    def search(self, query, limit=5, source_only=False, source_root='src'):
        if limit<1: raise ValueError('limit must be positive')
        if self.scope=='all':
            return self.index.search(query,limit,source_only,source_root)
        # Rank using original corpus statistics, then filter before top-k/fusion.
        ranked=self.index.search(query,max(1,len(self.records)),source_only,source_root)
        def eligible(row):
            p=PurePosixPath(row['path'])
            return p.suffix.lower()=='.md' and (self.root in p.parents or p.name.lower()=='readme.md')
        return [r for r in ranked if eligible(r)][:limit]
