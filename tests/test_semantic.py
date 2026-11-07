import unittest
import importlib.util
from semantic import fuse, HybridIndex


class SemanticTest(unittest.TestCase):
    def test_rrf_merges_same_citation_and_ignores_raw_score_scale(self):
        a = {'path':'a.py','start_line':1,'end_line':10,'score':1000}
        b = {'path':'b.py','start_line':1,'end_line':10,'score':.9}
        hits = fuse([[a,b],[b]],limit=2)
        self.assertEqual(hits[0]['path'],'b.py')
        self.assertAlmostEqual(hits[0]['score'],1/62+1/61)
        self.assertEqual(len(hits),2)
        self.assertEqual(len(fuse([[a,a]])),1)
        self.assertEqual(fuse([[],[]]),[])

    def test_hybrid_passes_same_scope_to_both_retrievers(self):
        class Fake:
            def __init__(self): self.calls=[]
            def search(self,*args): self.calls.append(args); return []
        a,b=Fake(),Fake()
        self.assertEqual(HybridIndex(a,b).search('question',5,True,'package'),[])
        self.assertEqual(a.calls,[('question',50,True,'package')])
        self.assertEqual(a.calls,b.calls)

    def test_lossless_token_windows_including_single_long_line(self):
        from semantic import safe_windows
        class Tokenizer:
            def encode(self, text, **kwargs): return list(text) + ['start','end']
        for text in ['one\ntwo\nthree\nfour', 'x'*100, '']:
            parts = safe_windows(text, Tokenizer(), 10)
            self.assertEqual(''.join(parts), text)
            self.assertTrue(all(len(Tokenizer().encode(p)) <= 10 for p in parts))
        with self.assertRaises(ValueError):
            safe_windows('x', Tokenizer(), 2)

    @unittest.skipUnless(importlib.util.find_spec("sentence_transformers"), "requires semantic virtual environment")
    def test_documents_reused_for_new_queries_and_invalidated_on_change(self):
        import tempfile
        import numpy as np
        from semantic import SemanticIndex
        calls = {'documents':0,'queries':0,'loads':0}
        class Tokenizer:
            def encode(self,text,**kwargs): return list(text)+[0,0]
        class Model:
            max_seq_length=20
            tokenizer=Tokenizer()
            prompts={}
            def encode_document(self,texts,**kwargs):
                calls['documents']+=1
                assert all(len(self.tokenizer.encode(t))<=20 for t in texts)
                return np.array([[1.,2.] for t in texts])
            def encode_query(self,texts,**kwargs):
                calls['queries']+=1
                return np.array([[1.,2.] for t in texts])
        def factory():
            calls['loads']+=1
            return Model()
        rows=[{'path':'a.py','text':'x'*100,'start_line':1,'end_line':1}]
        with tempfile.TemporaryDirectory() as cache:
            def build(q, revision='rev'):
                return SemanticIndex(rows,[q],'fixture',revision,cache,model_factory=factory)
            first=build('first')
            self.assertFalse(first.document_cache_hit)
            self.assertEqual(first.truncated,0)
            self.assertGreater(first.window_count,1)
            second=build('second')
            self.assertTrue(second.document_cache_hit)
            self.assertEqual(calls['documents'],1)
            self.assertEqual(calls['queries'],2)
            loads=calls['loads']
            third=build('second')
            self.assertEqual(third.query_cache_hits,1)
            self.assertEqual(calls['loads'],loads)
            self.assertEqual(third.search('second')[0]['text'],'x'*100)
            rows[0]['text']='changed'
            self.assertFalse(build('second').document_cache_hit)
            self.assertFalse(build('second',revision='new-rev').document_cache_hit)
