import copy
import io
import json
import unittest
from unittest.mock import patch
from answer import evidence_from_hits, validate_answer, parse_response, generate, payload


class AnswerTest(unittest.TestCase):
    def setUp(self):
        self.evidence=evidence_from_hits([{'path':'a.py','start_line':8,'end_line':9,'text':'def f():\n    return 1'}])
        self.answer={'status':'answered','claims':[{'text':'Returns one.','citations':[{
            'source_id':'S1','start_line':9,'end_line':9,'quote':'    return 1'}]}],'limitation':''}

    def test_valid_citation_and_reject_fabricated_source_lines_and_quotes(self):
        self.assertEqual(validate_answer(self.answer,self.evidence),self.answer)
        for field,value in [('source_id','S99'),('start_line',1),('end_line',100),('quote','return 2'),('start_line',True)]:
            answer=copy.deepcopy(self.answer)
            answer['claims'][0]['citations'][0][field]=value
            with self.assertRaises(ValueError): validate_answer(answer,self.evidence)
        self.answer['claims'][0]['citations']=[]
        with self.assertRaises(ValueError): validate_answer(self.answer,self.evidence)

    def test_refusal_incomplete_and_abstention(self):
        for response in [{'status':'incomplete'}, {'status':'completed','output':[{'content':[{'type':'refusal'}]}]}]:
            with self.assertRaises(ValueError): parse_response(response,self.evidence)
        answer={'status':'insufficient_evidence','claims':[],'limitation':'Missing context.'}
        self.assertEqual(validate_answer(answer,self.evidence),answer)

    def test_mocked_transport_and_no_evidence_skip(self):
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(self.answer)}]}],'usage':{'input_tokens':50}}
        with patch('answer.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result,usage=generate('What does f do?',self.evidence,'test-model','fake-test-key')
            self.assertEqual(result,self.answer)
            request=call.call_args.args[0]
            body=json.loads(request.data)
            self.assertFalse(body['store'])
            self.assertTrue(body['text']['format']['strict'])
            self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        with patch('answer.urllib.request.urlopen') as call:
            answer,_=generate('question',[],'test-model','fake')
            call.assert_not_called()
            self.assertEqual(answer['status'],'insufficient_evidence')

    def test_compatible_chat_request(self):
        content = {'status': 'insufficient_evidence', 'claims': [], 'limitation': 'Missing context.'}
        response = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(content)}}]}
        with patch.dict('os.environ', COMPATIBLE_BASE_URL='https://example.org/v1/'), patch('answer.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(response).encode())
            result, _ = generate('question', self.evidence, 'chosen-model', 'test-key', 'compatible')
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, 'https://example.org/v1/chat/completions')
            self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
            body = json.loads(request.data)
            self.assertEqual(body['model'], 'chosen-model')
            self.assertEqual(body['response_format'], {'type': 'json_object'})
            self.assertNotIn('thinking', body)
            self.assertEqual(result, content)

    def test_compatible_url_validation(self):
        from answer import compatible_endpoint
        for base in ['', 'http://example.org', 'https://user:pass@example.org', 'https://example.org/?key=x']:
            with self.subTest(base=base), patch.dict('os.environ', COMPATIBLE_BASE_URL=base), self.assertRaises(ValueError):
                compatible_endpoint()

    def test_context_budget_and_untrusted_data_separation(self):
        request=payload('question',self.evidence,'test-model')
        self.assertIn('untrusted',request['instructions'])
        self.assertEqual(json.loads(request['input'])['evidence'][0]['source_id'],'S1')
        self.evidence[0]['text']='x'*60001
        with self.assertRaises(ValueError): payload('question',self.evidence,'test-model')

    def test_deepseek_transport_and_citation_validation(self):
        response={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(self.answer)}}], 'usage':{'total_tokens':42}}
        with patch('answer.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result,usage=generate('question',self.evidence,'deepseek-flash','fake-deepseek-key',provider='deepseek')
            self.assertEqual(result,self.answer)
            request=call.call_args.args[0]
            self.assertEqual(request.full_url,'https://api.deepseek.com/chat/completions')
            body=json.loads(request.data)
            self.assertEqual(body['response_format'],{'type':'json_object'})
            self.assertEqual(body['thinking'],{'type':'disabled'})
            self.assertNotIn('store',body)
            self.assertIn('JSON',body['messages'][0]['content'])
            self.assertEqual(usage['total_tokens'],42)
        from answer import parse_deepseek_response
        self.answer['claims'][0]['citations'][0]['source_id']='invented'
        response['choices'][0]['message']['content']=json.dumps(self.answer)
        with self.assertRaises(ValueError): parse_deepseek_response(response,self.evidence)

    def test_deepseek_rejects_blank_truncated_and_invalid_output(self):
        from answer import parse_deepseek_response
        for reason,content in [('length','{}'),('stop','   '),('stop','not json'),('stop','{}')]:
            with self.assertRaises(ValueError):
                parse_deepseek_response({'choices':[{'finish_reason':reason,'message':{'content':content}}]},self.evidence)
        with patch('answer.urllib.request.urlopen') as call:
            with self.assertRaises(ValueError): generate('q',self.evidence,'m','k',provider='unknown')
            call.assert_not_called()

    def test_explicit_language_reaches_both_providers(self):
        from answer import deepseek_payload
        self.assertIn('REQUIRED OUTPUT LANGUAGE: English',payload('问题',self.evidence,'m','en')['instructions'])
        self.assertIn('REQUIRED OUTPUT LANGUAGE: Simplified Chinese',deepseek_payload('question',self.evidence,'m','zh')['messages'][0]['content'])
        self.assertEqual(json.loads(payload('q',self.evidence,'m','en')['input'])['evidence'][0]['numbered_text'],'8: def f():\n9:     return 1')
        with self.assertRaises(ValueError): payload('q',self.evidence,'m','invalid')
        answer,_=generate('q',[],'m','fake',language='zh')
        self.assertIn('未检索到',answer['limitation'])

    def test_trailing_blank_source_line_keeps_citation_range(self):
        evidence=evidence_from_hits([{'path':'docs/example.md','start_line':10,'end_line':11,'text':'example\n'}])
        answer={'status':'answered','claims':[{'text':'Example.','citations':[{'source_id':'S1','start_line':10,'end_line':11,'quote':'example\n'}]}],'limitation':''}
        self.assertEqual(validate_answer(answer,evidence),answer)

    def test_model_ranges_get_source_quotes_for_both_providers(self):
        from answer import parse_deepseek_response
        selected=copy.deepcopy(self.answer)
        del selected['claims'][0]['citations'][0]['quote']
        raw=json.dumps(selected)
        a=parse_response({'status':'completed','output':[{'content':[{'type':'output_text','text':raw}]}]},self.evidence)
        b=parse_deepseek_response({'choices':[{'finish_reason':'stop','message':{'content':raw}}]},self.evidence)
        self.assertEqual(a,self.answer)
        self.assertEqual(b,self.answer)
        self.assertNotIn('quote',selected['claims'][0]['citations'][0])
        schema=payload('q',self.evidence,'m')['text']['format']['schema']
        self.assertNotIn('quote',schema['properties']['claims']['items']['properties']['citations']['items']['properties'])

    def test_hydration_does_not_repair_bad_ranges_or_quotes(self):
        from answer import attach_source_quotes
        for field,value in [('source_id','missing'),('start_line',0),('end_line',99),('start_line',True)]:
            a=copy.deepcopy(self.answer)
            del a['claims'][0]['citations'][0]['quote']
            a['claims'][0]['citations'][0][field]=value
            with self.assertRaises(ValueError): attach_source_quotes(a,self.evidence)
        self.answer['claims'][0]['citations'][0]['quote']='wrong'
        with self.assertRaises(ValueError): attach_source_quotes(self.answer,self.evidence)
