# Portfolio description and interview notes

## Suggested GitHub description
Repository onboarding assistant with local hybrid retrieval, source-linked answers, and reproducible development evaluations.

## Resume draft
- Built a Python repository-onboarding RAG prototype combining BM25, local sentence embeddings, and reciprocal-rank fusion with configurable documentation search and DeepSeek/OpenAI generation adapters.
- Implemented token-safe embedding windows, independent document/query caches, and source-range validation; compared three retrievers on 16 development questions and added 30 automated tests.

Use these only if you can explain and demonstrate the implementation. This project was developed collaboratively with an AI coding assistant. Do not imply independent authorship of every line, production deployment, real users, or independently validated accuracy.

## Discussion topics
- Why retrieval scores are not probabilities of correctness.
- Why source-only filtering helped implementation questions but excluded onboarding documentation.
- Why syntax-aware chunking did not improve every metric.
- How token-safe pooling avoids input truncation but can dilute a relevant passage.
- Why query/document cache keys are separate and how policy/model changes invalidate caches.
- Why extracting a quotation from selected line ranges improves reference integrity without proving entailment.
- How JSON-object output differs from strict structured output and why local validation is required.

## Claim boundaries
The prototype is a local CLI. The 16-question set is a development set, labels await independent review, and model-answer testing is limited. No hosted endpoint, production SLA, comprehensive multilingual retrieval evaluation, or completed red-team assessment is claimed.
