import copy
import unittest
from quality import check_run


class QualityTest(unittest.TestCase):
    def setUp(self):
        self.case={'id':'fixture','question':'What does f return?','language':'en',
                   'expected_status':'answered','required_mentions':['returns'], 'review_rubric':[]}
        self.run={'question':self.case['question'],'evidence':[{'source_id':'S1','path':'a.py','start_line':1,'end_line':1,'text':'return 1'}],
                  'answer':{'status':'answered','claims':[{'text':'返回 1。','citations':[{'source_id':'S1','start_line':1,'end_line':1,'quote':'return 1'}]}],'limitation':''}}

    def test_flags_do_not_claim_semantic_correctness(self):
        r=check_run(self.run,self.case)
        self.assertTrue(r['citation_integrity']['passed'])
        self.assertTrue(r['language_review_flag'])
        self.assertEqual(r['missing_required_mentions'],['returns'])
        self.assertEqual(r['correctness'],'manual_review_required')
        self.run['answer']['claims'][0]['text']='This returns two.'
        r=check_run(self.run,self.case)
        self.assertEqual(r['missing_required_mentions'],[])
        self.assertEqual(r['citation_support'],'manual_review_required')

    def test_bad_citation_and_case_mismatch(self):
        self.run['answer']['claims'][0]['citations'][0]['quote']='return 2'
        self.assertFalse(check_run(self.run,self.case)['citation_integrity']['passed'])
        self.run['question']='different'
        with self.assertRaises(ValueError): check_run(self.run,self.case)

    def test_abstention_and_chinese_requirement(self):
        self.case.update(expected_status='insufficient_evidence',language='zh',required_mentions=[])
        self.run['answer']={'status':'insufficient_evidence','claims':[],'limitation':'证据不足。'}
        r=check_run(self.run,self.case)
        self.assertTrue(r['expected_status_match'])
        self.assertFalse(r['language_review_flag'])

    def test_saved_explicit_language_overrides_question_default(self):
        self.run['language']='zh'
        report=check_run(self.run,self.case)
        self.assertEqual(report['expected_language'],'zh')
        self.assertFalse(report['language_review_flag'])
