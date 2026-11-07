import unittest
from chunking import chunks


class ChunkingTest(unittest.TestCase):
    def test_method_decorator_and_exact_source_coverage(self):
        text = 'import os\n\nclass Example:\n    @staticmethod\n    async def run():\n        return 1\n\nx = 2\n'
        rows = list(chunks(text, syntax=True))
        method = next(r for r in rows if r['symbol'])
        self.assertEqual(method['symbol'], 'Example.run')
        self.assertEqual((method['start_line'], method['end_line']), (4, 6))
        covered = set()
        for r in rows:
            covered.update(range(r['start_line'], r['end_line']+1))
            self.assertEqual(r['text'], '\n'.join(text.splitlines()[r['start_line']-1:r['end_line']]))
        self.assertEqual(covered, set(range(1, 9)))

    def test_long_function_retains_symbol_without_duplicate_nested_function(self):
        text = 'def outer():\n    def inner():\n        pass\n' + '    x = 1\n' * 20
        rows = list(chunks(text, size=8, overlap=2, syntax=True))
        self.assertTrue(all(r['symbol'] == 'outer' for r in rows))
        self.assertTrue(all(r['end_line']-r['start_line']+1 <= 8 for r in rows))
        self.assertEqual(rows[-1]['end_line'], 23)
        self.assertEqual(rows[1]['start_line'], 7)

    def test_invalid_syntax_falls_back_and_empty_input(self):
        rows = list(chunks('def broken(', syntax=True))
        self.assertEqual(rows[0]['chunk_mode'], 'syntax-fallback')
        self.assertEqual(rows[0]['text'], 'def broken(')
        self.assertEqual(list(chunks('', syntax=True)), [])
