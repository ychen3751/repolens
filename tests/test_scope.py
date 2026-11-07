import unittest
from search import SearchIndex
from retrieval_scope import ScopedIndex
from semantic import HybridIndex


class ScopeTest(unittest.TestCase):
    def test_directory_boundary_readme_and_no_fallback(self):
        paths=['docs/usage.md','README.md','pkg/README.md','docs_extra/usage.md','tests/test.py','src/api.py','manual/start.md']
        rows=[{'path':p,'text':'invoke','start_line':1,'end_line':1} for p in paths]
        base=SearchIndex(rows)
        guide=ScopedIndex(base,rows,'guide')
        self.assertEqual({r['path'] for r in guide.search('invoke',10)},set(paths[:3]))
        all_hits=base.search('invoke',10)
        self.assertEqual(ScopedIndex(base,rows).search('invoke',10),all_hits)
        for hit in guide.search('invoke',10):
            self.assertEqual(hit['score'],next(r['score'] for r in all_hits if r['path']==hit['path']))
        self.assertIn('manual/start.md',[r['path'] for r in ScopedIndex(base,rows,'guide','manual').search('invoke',10)])
        self.assertEqual(guide.search('missing'),[])
        with self.assertRaises(ValueError): ScopedIndex(base,rows,'guide','../docs')
        fused=HybridIndex(guide,guide).search('invoke',3)
        self.assertTrue(all(r['path'] in paths[:3] for r in fused))
