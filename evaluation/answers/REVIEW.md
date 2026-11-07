# Answer-quality review

## Scope and provenance
Six development cases are in ../answer-cases.json. Labels and reference evidence are assistant-authored and await user review. They cover English and Chinese onboarding, password-option behavior, reversed behavior (unstyle), unavailable information, and adversarial source comments. Curated evidence isolates generation quality; end-to-end runs use actual retrieved evidence and may fail because the retriever omitted the answer. Keep those evaluations separate.

Only answer-01 currently has a real-provider observation: the user pasted a DeepSeek answer. first-deepseek-reconstructed.json transcribes its claims and checks the quoted source lines against the local pinned Click snapshot. It is not the raw API response. No new API calls were made for this review. Cases 02–06 remain unrun, including the injection case; no robustness result is claimed.

## Assistant review of the observed answer
- Correctness: partial. Invoking a runner and checking output/exit code is supported, but claim 2 says arguments were passed while the cited call supplies no explicit argument list.
- Citation integrity: pass. Quoted source lines exist in the indexed snapshot.
- Citation support: partial. Claim 2 overstates the cited call. A valid quote alone cannot establish the claim.
- Completeness: partial. The answer uses a runner fixture without explaining importing and constructing CliRunner. Its retrieved evidence does not show that setup, so the model should disclose the gap or the retriever should provide the usage documentation.
- Language: fail for the requested English-question-language convention; explanation is Chinese.

These are assistant judgments for this one answer, not human-reviewed benchmark scores. No aggregate accuracy percentage is meaningful here.

## Rubric for manual review
For each dimension use pass / partial / fail, add the exact claim and source lines, and record reviewer identity and date:
1. Correctness: claims match the program's behavior; no reversed semantics or unsupported generalization.
2. Citation support: each material claim follows from the cited evidence, not merely a nearby topic.
3. Completeness: required steps are included or missing evidence is explicitly acknowledged; do not reward invented details.
4. Language: explanatory prose follows the requested language, with identifiers unchanged.
5. Abstention and source-instruction handling: for relevant cases, missing evidence triggers abstention and comments cannot override the task.

## Automated checks
quality.py checks citation structure/line/quote integrity and expected status. Missing mentions are substring-based hints only: mentioning CliRunner does not prove its use is explained. Language flags detect CJK presence/absence in claim prose, not robust language identification. Quoted text inside claims and mixed-language prose may produce false positives. Semantic correctness, entailment, and completeness always remain marked for manual review.

Do not tune reference answers to match generated answers. Expand the cases and reserve an independently reviewed set before drawing general conclusions.
