import unittest
from evaluate import first_rank, evaluate


class EvaluateTest(unittest.TestCase):
    def test_requires_full_span_and_correct_file(self):
        evidence = [{'path': 'a.py', 'start_line': 10, 'end_line': 15}]
        rows = [{'path': 'b.py', 'start_line': 1, 'end_line': 80},
                {'path': 'a.py', 'start_line': 1, 'end_line': 12},
                {'path': 'a.py', 'start_line': 10, 'end_line': 20}]
        self.assertEqual(first_rank(rows, evidence), 3)
        self.assertIsNone(first_rank(rows[:2], evidence))

    def test_metrics_and_version_guard(self):
        rows = [{'path':'a.py','start_line':1,'end_line':20,'text':'token',
                 'base_commit':'abc','working_tree_dirty':False}]
        data = {'commit':'abc','split':'development','label_review':'fixture','questions':[
            {'id':'one','question':'token','evidence':[{'path':'a.py','start_line':2,'end_line':3}]},
            {'id':'two','question':'missing','evidence':[{'path':'a.py','start_line':2,'end_line':3}]}]}
        report = evaluate(rows, data)
        self.assertEqual(report['hit_at_5'], .5)
        self.assertEqual(report['mrr_at_5'], .5)
        rows[0]['working_tree_dirty'] = True
        with self.assertRaises(ValueError):
            evaluate(rows, data)
