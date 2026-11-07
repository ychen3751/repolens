"""Offline answer checks. Flags are review aids, not semantic accuracy scores."""
import argparse
import json
from pathlib import Path
import re
from answer import validate_answer


def check_run(run, case):
    if run['question'] != case['question']:
        raise ValueError('Run question differs from selected case')
    answer=run['answer']
    try:
        validate_answer(answer,run['evidence'])
        integrity={'passed':True,'error':None}
    except (ValueError,KeyError,TypeError) as exc:
        integrity={'passed':False,'error':str(exc)}
    prose=' '.join(c.get('text','') for c in answer.get('claims',[]) if isinstance(c,dict))+' '+answer.get('limitation','')
    cjk=bool(re.search(r'[\u3400-\u9fff]',prose))
    requested=run.get('language','auto')
    expected_language=case['language'] if requested=='auto' else requested
    if expected_language not in ('en','zh'): raise ValueError('Unsupported review language')
    language_flag=(expected_language=='en' and cjk) or (expected_language=='zh' and not cjk)
    missing=[term for term in case.get('required_mentions',[]) if term.casefold() not in prose.casefold()]
    return {'case_id':case['id'],'provenance':run.get('provenance','unspecified'),
            'citation_integrity':integrity,
            'expected_status_match':answer.get('status')==case['expected_status'],
            'expected_language':expected_language,'language_review_flag':language_flag,
            'missing_required_mentions':missing,
            'correctness':'manual_review_required','citation_support':'manual_review_required',
            'completeness':'manual_review_required',
            'review_rubric':case['review_rubric']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,default=Path('evaluation/answers/first-deepseek-reconstructed.json'))
    p.add_argument('--cases',type=Path,default=Path('evaluation/answer-cases.json'))
    p.add_argument('--case',default='answer-01')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not a.run.is_file():
        p.error(f'Run record not found: {a.run}. A failed generation/validation does not save a successful run. Check answer.py output first.')
    case=next((c for c in json.loads(a.cases.read_text())['cases'] if c['id']==a.case),None)
    if case is None: p.error('Unknown case id')
    report=check_run(json.loads(a.run.read_text()),case)
    text=json.dumps(report,ensure_ascii=False,indent=2)
    print(text)
    if a.output:
        if a.output.exists(): p.error('Output exists; choose a new filename')
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(text+'\n')


if __name__=='__main__': main()
