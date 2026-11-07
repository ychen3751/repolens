import subprocess
import tempfile
import unittest
from pathlib import Path
from ingest import ingest


class IngestTest(unittest.TestCase):
    def test_citations_overlap_and_dirty_state(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            def git(*args):
                subprocess.run(['git', '-C', d, *args], check=True, capture_output=True)
            git('init')
            (root / 'sample.py').write_text('\n'.join(f'# line {i}' for i in range(1, 102)))
            (root / 'untracked.md').write_text('must not appear')
            git('add', 'sample.py')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
            rows = ingest(root)
            self.assertEqual([(r['start_line'], r['end_line']) for r in rows], [(1, 80), (66, 101)])
            self.assertTrue(all(r['path'] == 'sample.py' for r in rows))
            self.assertFalse(rows[0]['working_tree_dirty'])
            self.assertEqual(rows[1]['text'].splitlines()[0], '# line 66')
            old_hash = rows[0]['file_sha256']
            (root / 'sample.py').write_text('# changed')
            modified = ingest(root)[0]
            self.assertTrue(modified['working_tree_dirty'])
            self.assertNotEqual(old_hash, modified['file_sha256'])

    def test_invalid_overlap(self):
        with self.assertRaises(ValueError):
            ingest(Path('.'), size=10, overlap=10)
