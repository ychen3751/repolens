import unittest
from search import SearchIndex, tokenize


class SearchTest(unittest.TestCase):
    def test_ranking_and_no_match(self):
        rows = [{'path': 'auth.py', 'start_line': 1, 'text': 'validate authentication token'},
                {'path': 'other.py', 'start_line': 1, 'text': 'render template'}]
        index = SearchIndex(rows)
        self.assertEqual(index.search('authentication token')[0]['path'], 'auth.py')
        self.assertEqual(index.search('nonexistent'), [])
        self.assertEqual(index.search('the and'), [])
        self.assertEqual(SearchIndex([]).search('token'), [])
        with self.assertRaises(ValueError):
            index.search('token', 0)

    def test_identifier_splitting(self):
        self.assertEqual(tokenize('resolveCommand resolve_command'), ['resolve', 'command', 'resolve', 'command'])

    def test_source_filter_preserves_scores_and_checks_directory_boundary(self):
        rows = [{'path': p, 'start_line': 1, 'text': 'token authentication'} for p in
                ['docs/auth.md', 'tests/test_auth.py', 'src/auth.py',
                 'src_extra/auth.py', 'src/notes.md', 'package/auth.py']]
        index = SearchIndex(rows)
        all_hits = index.search('token', 10)
        source_hits = index.search('token', 10, source_only=True)
        self.assertEqual([r['path'] for r in source_hits], ['src/auth.py'])
        original = next(r for r in all_hits if r['path'] == 'src/auth.py')
        self.assertEqual(source_hits[0]['score'], original['score'])
        self.assertEqual(index.search('token', source_only=True, source_root='package')[0]['path'], 'package/auth.py')
        self.assertEqual(index.search('token', source_only=True, source_root='missing'), [])
        with self.assertRaises(ValueError):
            index.search('token', source_only=True, source_root='../src')

    def test_symbol_metadata_is_opt_in_and_does_not_change_citations(self):
        row = {'path': 'src/core.py', 'start_line': 42, 'end_line': 43,
               'text': 'def run():\n    pass', 'symbol': 'UniqueContainer.run'}
        self.assertEqual(SearchIndex([row]).search('container'), [])
        hit = SearchIndex([row], symbol_context=True).search('container')[0]
        self.assertEqual(hit['text'], row['text'])
        self.assertEqual((hit['start_line'], hit['end_line']), (42, 43))
        legacy = {k: v for k, v in row.items() if k != 'symbol'}
        self.assertEqual(SearchIndex([legacy], symbol_context=True).search('run'),
                         SearchIndex([legacy]).search('run'))
