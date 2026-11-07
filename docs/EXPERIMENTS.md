# Development history and experiments

This is a chronological archive. Early implementation status and next steps describe earlier stages and may be superseded by later entries. For current capabilities and setup, see [the project README](../README.md). Commands assume the repolens directory. English is now the default answer language; use --language auto explicitly for the earlier question-language behavior.

# RepoLens

A repository onboarding assistant, built incrementally as a learning project.

## Current implementation
Local Git ingestion for tracked UTF-8 Python and Markdown files. Uses only Python's standard library and Git. Files are split into 80-line windows with 15-line overlap. Each chunk retains its path, line range, file hash, base commit, and working-tree dirty flag. Source code is never executed.

```bash
cd repolens
python3 ingest.py /absolute/path/to/repository --output /tmp/repolens-chunks.jsonl
python3 -m unittest discover -s tests -v
```

The source repository must have at least one commit. Output must be outside that repository. Symlinks, unsupported formats, files over 1 MB, and undecodable files are skipped. This baseline does not parse function/class boundaries. A dirty working tree means citations describe local content, not necessarily the base commit. Do not build commit permalinks for dirty content without verification. Tracked files can contain sensitive content: review your chosen corpus before sending chunks to an external model.

## Product scope
Answer questions about repository setup, implementation locations, and code flow with verified file/line citations. First target: one public Python repository at a recorded commit.

## Next milestones
1. Select and ingest a small public repository; manually inspect chunk boundaries.
2. Implement keyword retrieval and write reviewed question/evidence pairs.
3. Compare embeddings and hybrid retrieval against the baseline on held-out questions.
4. Add answer generation with citations and insufficient-evidence handling.
5. Build a demo/API and publish measured results and reproducible instructions.

BM25 keyword retrieval is implemented. LLM generation, UI, deployment, and held-out quality evaluation are not implemented yet.

## Today's learning exercise
Read ingest.py, then explain:
- Why do we retain line numbers and a file hash?
- Why might the base commit disagree with local file contents?
- How can splitting a function across chunks hurt retrieval?
- What do we gain and lose by overlapping adjacent chunks?

The earlier PolicyLens prototype is preserved separately; RepoLens is the active project.


## Run the keyword baseline

```bash
python3 search.py data/click.jsonl "resolve command" --limit 3
```

The index is generated locally and excluded from Git. The first corpus is
https://github.com/pallets/click at commit
`ac0e297ec2d7d78455a7d18ce306996e668c4a85`.
It contains 650 chunks from 128 tracked Python/Markdown files. All 650 chunk line ranges were checked against local source text. This checks citation alignment, not answer relevance.

To reproduce the corpus (Git and network access required):

```bash
git clone https://github.com/pallets/click.git /tmp/repolens-click
git -C /tmp/repolens-click checkout ac0e297ec2d7d78455a7d18ce306996e668c4a85
python3 ingest.py /tmp/repolens-click --output data/click.jsonl
```

The public source remains in its own checkout with its original license. No source code is executed during ingestion. BM25 runs locally with no model API or embedding costs. It splits snake_case and basic camelCase identifiers and ranks lexical matches. Scores are not probabilities. English keyword search is the current baseline; Chinese questions, synonyms, overlapping duplicate hits, and function boundaries remain limitations.

Observed development example: `resolve command` ranks `docs/complex.md:326-386` first. This is relevant documentation but not necessarily the implementation a user wanted. Next: define reviewed question/evidence pairs before tuning ranking. No retrieval accuracy metric has been established.


## Development evaluation

```bash
python3 evaluate.py
```

Labels: `evaluation/click-dev.json`. Saved baseline: `evaluation/bm25-baseline.json`.
Eight implementation-location questions were authored and checked against source by the assistant; user review remains pending. They are development questions, not an independent test set or a comprehensive relevance judgment pool.

A hit requires a retrieved chunk to fully contain a labeled evidence span in the correct file. Hit@k is the fraction of questions with at least one such hit among the first k results. MRR@5 averages the reciprocal first-hit rank, with zero for a miss. Overlapping chunks remain separate ranked results, matching the current CLI behavior. These metrics do not measure generated answer correctness or full-function coverage.

Baseline: Hit@1 = 2/8 (25%); Hit@3 = 5/8 (62.5%); Hit@5 = 5/8 (62.5%); MRR@5 = 0.4167. This small, implementation-focused development set cannot support general accuracy or resume improvement claims. No ranking changes were made in this evaluation step. The evaluator rejects mismatched commits, dirty indexed content, and evidence unavailable in the index.

Next learning exercise: inspect a failed question and its evidence span, then explain why keyword overlap favored a different passage. Expand and user-review the development set, and reserve independently authored questions for later held-out evaluation before tuning retrieval.

## Experiment 1: implementation-only candidates

```bash
python3 search.py data/click.jsonl "Where does the password option enable hidden input and confirmation?" --source-only --limit 3
python3 evaluate.py --source-only
```

`--source-only` restricts candidates to `.py` files under `src/`. For another repository layout, supply `--source-root package_name`. This is an explicit directory filter, not automatic intent detection or classification of production code. Files such as tests nested within that directory are not specially excluded. Repositories without a matching directory return no matches.

BM25 statistics are still computed over the complete index. Filtering occurs before top-k selection, preserving the scores and relative order of eligible chunks. This isolates candidate filtering from changes in IDF or average document length. Default full-repository retrieval remains unchanged.

| Development metric | All files | Source only |
|---|---:|---:|
| Hit@1 | 2/8 (25%) | 4/8 (50%) |
| Hit@3 | 5/8 (62.5%) | 6/8 (75%) |
| Hit@5 | 5/8 (62.5%) | 6/8 (75%) |
| MRR@5 | 0.4167 | 0.6250 |

Report: `evaluation/bm25-source-only.json`. Password option implementation moves into rank 2; command resolution and styled output still miss the top 5. These eight development questions specifically ask for implementation, so this result does not establish an improvement for documentation or general onboarding questions. Keep all-files search as the default. Next experiments should investigate remaining misses and broaden reviewed questions before evaluating on a held-out set.

## Inspect remaining failures

```bash
python3 diagnose.py
```

See `evaluation/failure-analysis.md` for source-checked observations. The implementation evidence for dev-01 ranks 40 and dev-06 ranks 37 in source-only mode. Fixed windows lose enclosing-class context or split function headers from implementation; token forms also differ between questions and code. The proposed next experiment is optional syntax-aware chunking, evaluated independently of scoring changes.

## Experiment 2: syntax-aware Python chunks

```bash
python3 ingest.py /private/tmp/repolens-click --syntax --output data/click-syntax.jsonl
python3 evaluate.py --index data/click-syntax.jsonl --source-only
python3 search.py data/click-syntax.jsonl "password confirmation" --source-only --limit 3
```

Adjust the checkout path if cloned elsewhere. The original data/click.jsonl remains unchanged.

Python is parsed with the standard-library AST without executing it. Functions and methods form regions including decorators. Nested functions remain within their enclosing function. Class headers, module-level code, and other gaps are retained in separate regions so no lines disappear. Markdown keeps fixed windows. Regions longer than 80 lines are split with 15-line overlap. Invalid or unsupported Python syntax falls back to fixed windows with `chunk_mode: syntax-fallback`. Parser support depends on the Python interpreter version.

Each chunk has `symbol` (for example `Group.resolve_command`) and `chunk_mode`. Source text is verbatim; metadata is not inserted into source or used for BM25 scoring in this experiment. That keeps the scoring inputs to path + text, as before. BM25's formula and parameters stay unchanged, but its corpus statistics naturally change with the new chunks.

At the pinned Click commit the new index contains 2,824 chunks from 128 files (2,674 syntax chunks and 150 fixed Markdown chunks; no syntax fallbacks). All line ranges and text were checked against the checkout, all indexed-file lines remain covered, and all chunks satisfy the 80-line limit. The original fixed-window evaluation reproduces unchanged.

| Source-only development metric | Fixed windows | Syntax regions |
|---|---:|---:|
| Hit@1 | 50% | 50% |
| Hit@3 | 75% | 75% |
| Hit@5 | 75% | 75% |
| MRR@5 | 0.625 | 0.625 |

Reports: `evaluation/bm25-syntax.json` and `evaluation/syntax-misses.json`.
Password option improves from rank 2 to 1; confirmation prompt worsens from 1 to 2. Command resolution moves from rank 40 to 57; styled output improves from 37 to 15 but remains outside the top five. These are observed development results, not a quality improvement claim. More coherent boundaries alone did not improve aggregate metrics on these eight questions. Additional small gap chunks also change corpus statistics and candidate competition.

Next isolated experiment: index the already-preserved symbol metadata, or investigate token normalization separately. Keep this unsuccessful aggregate result in the experiment record; do not silently replace the baseline or tune labels to improve metrics.

## Experiment 3: include symbol metadata

```bash
python3 evaluate.py --index data/click-syntax.jsonl --source-only --symbol-context
python3 search.py data/click-syntax.jsonl "Where is command resolution implemented for a group?" --source-only --symbol-context --limit 3
```

The optional `--symbol-context` flag appends the stored qualified symbol once to the internal BM25 input, alongside path and source text. It uses the same tokenizer, formula, candidate filter, and source chunks. Term counts, document lengths, and corpus statistics are recomputed for this input. Original source text and citation ranges are untouched. No special weight or question-specific rule is added. Legacy records without symbol metadata still work; such records receive no extra context. The flag is disabled by default.

Report: `evaluation/bm25-syntax-symbols.json`. On the same eight development questions, Hit@1 remains 50%, Hit@3 and Hit@5 remain 75%, and MRR@5 remains 0.625. All eight top-five evidence ranks are unchanged. In the complete source-only ranking, command-resolution evidence moves from rank 57 to 35; styled-output evidence moves from 15 to 17. This experiment does not establish an aggregate improvement. Eleven tests pass, including opt-in behavior, legacy-index compatibility, and citation preservation; disabling the flag reproduces the prior syntax baseline.

The remaining mismatch includes query vocabulary versus implementation vocabulary. Before further tuning, expand the reviewed question set beyond these same eight implementation questions and reserve an independent evaluation set. Subsequent semantic-retrieval experiments should compare against the recorded lexical baselines, not treat richer metadata as automatically better.

## Experiment 4: local semantic and hybrid retrieval

The expanded development set has 16 assistant-authored, source-checked questions (including the original eight). Added questions cover CLI examples, testing, error display, stream handling, and option normalization. User label review remains pending. This is NOT a held-out set; independent evaluation remains future work.

Run from the repolens directory:

```bash
# Existing local installation:
.venv/bin/python compare.py

# Search with local embeddings or hybrid retrieval:
.venv/bin/python semantic.py data/click-syntax.jsonl "How do I test a command and inspect its output?" --hybrid --limit 3

# Fresh environment (Python 3.12 was used here):
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-semantic.lock.txt
```

The embedding model is `sentence-transformers/all-MiniLM-L6-v2`, pinned in `evaluation/embedding-model.json`. It is a small general-language baseline, not a claim of state-of-the-art code retrieval. Model files download on first use; inference then runs locally on CPU with no paid API calls. Only model requests are sent to the model host, not corpus content. Implementation follows https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html .

All methods use the SAME 2,824 syntax-index chunks and full-repository scope, with symbol metadata included. Full scope is necessary for the documentation questions. Do not directly compare these percentages to the earlier eight-question source-only experiment.

Semantic retrieval uses normalized vectors and dot products (cosine similarity). Hybrid uses reciprocal rank fusion with constant 60 and the top 50 candidates from each method; raw BM25 and cosine scores are not added together. No relevance threshold or answerability detector has been calibrated.

| Metric (16 development questions) | BM25 | Semantic | Hybrid |
|---|---:|---:|---:|
| Hit@1 | 3/16 (18.75%) | 5/16 (31.25%) | 6/16 (37.5%) |
| Hit@3 | 8/16 (50%) | 6/16 (37.5%) | 7/16 (43.75%) |
| Hit@5 | 8/16 (50%) | 8/16 (50%) | 9/16 (56.25%) |
| MRR@5 | 0.3229 | 0.3688 | 0.4344 |

Report: `evaluation/retrieval-comparison.json` includes model revision, library versions, index/dataset hashes, per-question results, and truncation count. These are implementation measurements on a small development set, not general accuracy claims. Evidence labels are not exhaustive: other valid passages may be scored as misses.

### Known limitations
- Historical experiment 4: 530 of 2,824 chunks were truncated at 256 tokens. Experiment 5 below replaces that behavior with token-safe windows.
- Historical experiment 4 used a combined corpus/query cache. Experiment 5 below separates document and individual-query caches.
- Preparation time includes loading/download or cache handling and is NOT per-query latency. No production latency benchmark is claimed.
- The broader set has no unanswerable questions or independently held-out cases yet. Dense similarity alone does not establish that an answer exists.
- Historical experiment 4 had no answer generation. Token truncation was addressed in experiment 5; the API answer interface is documented below. Live answer-quality evaluation and UI remain pending.

## Experiment 5: independent caches and token-safe windows (current default)

```bash
.venv/bin/python compare.py
.venv/bin/python semantic.py data/click-syntax.jsonl "How do I test a command and inspect its output?" --hybrid --limit 3
```

`compare.py` now writes `evaluation/retrieval-comparison-windowed.json`; the original truncated-model report is preserved. Old combined caches are ignored, not deleted.

Document caches depend on corpus text/order, model revision, encoder library versions, and the embedding-policy version; they do not depend on questions. Each query has its own cache key independent of the corpus. Writes use atomic replacement. Cached citation metadata is never reused: results attach to the current supplied source records. A new question loads the model and embeds only that question; a repeated question can use both caches without loading the model. Changing documents rebuilds the corpus cache; incremental per-file updates are not implemented.

Before encoding, each full input (path, symbol, source text) is partitioned into windows measured with the model's actual tokenizer, including special tokens. Splits prefer nearby newlines; unusually long single lines can split at character boundaries. Concatenating the windows recovers the complete original input. Each window is within 256 tokens. Window embeddings are averaged and normalized into one vector for the original chunk, preserving its original source citation. This policy also handles long queries. Models with nonempty prompts are rejected because prompt token budgets are not yet supported.

Actual corpus: 2,824 source chunks produce 4,033 embedding windows. The 530 previously truncated chunks are now split; zero chunks are truncated. No original source index or citation line range changes. Averaging windows can dilute a specific passage's signal; preserving input coverage does not guarantee retrieval quality.

| Metric | Semantic before | Semantic now | Hybrid before | Hybrid now |
|---|---:|---:|---:|---:|
| Hit@1 | 5/16 | 6/16 | 6/16 | 5/16 |
| Hit@3 | 6/16 | 7/16 | 7/16 | 7/16 |
| Hit@5 | 8/16 | 9/16 | 9/16 | 9/16 |
| MRR@5 | 0.3688 | 0.4313 | 0.4344 | 0.3927 |

Same 16 development questions and full-corpus scope; BM25 is unchanged. No claim that hybrid always wins or that these results generalize.

Cache verification (`evaluation/cache-verification.json`): a new question reused document vectors (about 3.30 seconds including model loading); immediately repeating it reused both caches without loading the model (about 0.019 seconds). These are one-process initialization observations, not end-to-end latency percentiles or a production benchmark. The CLI now prints cache hits and window count. Fifteen tests pass in the semantic virtual environment, including lossless splits, long lines, cache invalidation, new-query corpus reuse, and unchanged source citations.

## Cited answers: API integration (live validation pending)

Three explicit modes are available. Existing keyword search and evaluation still need no generation API key.

```bash
# Fully offline, hand-authored synthetic illustration (not an LLM benchmark):
python3 answer.py --demo

# Retrieve real repository evidence without a generation API call:
python3 answer.py --preview "Where is password confirmation configured?" --top-k 3

# Optional semantic/hybrid retrieval uses the project's semantic environment:
.venv/bin/python answer.py --preview "How do I test a command?" --retriever hybrid
```

The fixed demo has a tiny synthetic greeting function. It does not claim to be a previously generated answer or a real retrieval result. Preview displays the exact source records available for live generation.

### Configure live generation locally

Only exported environment variables are read; `.env` files are not automatically loaded. `.env.example` is a blank configuration template. The key and model must both be supplied. Use a model enabled for your OpenAI account that supports Responses Structured Outputs. No default model or pricing assumption is baked into the code.

For Bash, input the key without echoing it or placing its value in shell history:

```bash
read -s -p "OpenAI API key: " OPENAI_API_KEY
export OPENAI_API_KEY
printf '\n'
read -p "OpenAI model ID: " OPENAI_MODEL
export OPENAI_MODEL
.venv/bin/python answer.py --live "How do I test a command and inspect its output?" --retriever hybrid
```

`--live` sends the question and up to five retrieved snippets (configurable 1–10) to OpenAI and incurs API charges on your account. Review the corpus before using private code. This is a local CLI, not a public hosted endpoint. Never put API keys into source, screenshots, logs, or Git. Real `.env` variants are ignored; `.env.example` is allowed. Secret scanning and history review are still needed before publication.

### Answer contract and limits

The standard-library HTTP client calls `https://api.openai.com/v1/responses` with `store: false`, a strict JSON schema, a 2,000-token output cap, a 60-second timeout, and no automatic retries. `store: false` is a request setting, not a guarantee about all provider retention policies. Requests exceeding 60,000 characters of question/evidence fail rather than silently trimming citations. Model-context and account-access limits can still reject a request.

The prompt treats repository content as untrusted evidence and requires abstention when evidence is insufficient. Output is a list of claims, each with a source ID, inclusive line range, and exact quote. Local validation rejects unknown sources, out-of-range lines, mismatched quotes, uncited claims, refusals, incomplete responses, and malformed output. Citations refer to the indexed snapshot and show its base commit and dirty flag; they are not a fresh check against a changed checkout.

Citation validation verifies reference integrity, NOT factual support or semantic entailment. A claim can misinterpret a valid quotation. Human review and a separate grounded-answer evaluation are still required. Prompt instructions reduce risk but are not a complete prompt-injection defense. No tools are exposed to the model and no returned code is executed.

API contract source: https://developers.openai.com/api/docs/guides/structured-outputs .

### Verification status

19 automated tests pass in the semantic virtual environment. Coverage includes real-index offline preview, mocked HTTP request/response handling, no-evidence call skipping, refusal/incomplete output rejection, and citation tampering. No real generation API request has been run or measured; configure credentials and run a live smoke check before calling this production-ready. Nothing has been published to GitHub or deployed by this step.

## DeepSeek generation option

OpenAI remains the default; choose DeepSeek explicitly with `--provider deepseek`.
DeepSeek uses its own key and model variables, never falls back to OpenAI credentials,
and sends live requests only to `https://api.deepseek.com/chat/completions`.

Run the first command, paste the key at its prompt, and press Enter before continuing:

```bash
read -r -s -p "DeepSeek API key: " DEEPSEEK_API_KEY
export DEEPSEEK_API_KEY
export DEEPSEEK_MODEL=deepseek-flash
.venv/bin/python answer.py --live --provider deepseek \
  "How do I test a command and inspect its output?" --retriever hybrid --top-k 3
```

DeepSeek API calls are paid; a free chat interface does not imply free API access.
No OpenAI key is required for this provider. The documented default as checked on
2026-11-06 is `deepseek-flash`; override DEEPSEEK_MODEL to use another compatible
model available to your account. This adapter requests non-thinking mode, JSON-object
output, and a 2,000-token maximum. It does not use OpenAI Responses or its strict
server-side JSON schema. The desired schema and an abstention example are supplied
in the prompt, and the same local structural and citation checks still apply.

Blank JSON content, malformed content, non-stop finish reasons, and invalid citations
are rejected, with no automatic retry or automatic fallback to another provider.
This avoids surprise retry costs but may require you to refine the query manually.

Verification: 21 tests pass, including mocked requests for both providers and
DeepSeek blank/truncated/invalid responses. Real-index preview works without a key.
No paid DeepSeek request has been made or answer quality measured yet.

Official references:
- https://api-docs.deepseek.com/guides/json_mode/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/ (current model identifiers and API setup)

## Answer-quality development checks

```bash
# Offline review of the first user-observed DeepSeek answer (no paid calls):
python3 quality.py

# Optional new paid run, explicitly requested by --live, saved for review:
.venv/bin/python answer.py --live --provider deepseek \
  "How do I test a command and inspect its output?" --retriever hybrid --top-k 3 \
  --save-run data/answers/onboarding-01.json

# Offline checks of that saved run:
python3 quality.py --run data/answers/onboarding-01.json --case answer-01
```

Run records include question, validated answer, retrieved source evidence, provider/model, and usage; no API key or request headers are saved. They may contain private code/question content: keep private runs under ignored data/. Existing files are not overwritten. Validation failures do not produce a successful run record. Review records describe the model response and supplied evidence, not a fresh validation of the checkout.

Six development cases and curated reference evidence are in evaluation/answer-cases.json. Only the first has been observed with a live provider; others are prepared but unrun. The first run was reconstructed from user-pasted terminal output and is labeled accordingly. See evaluation/answers/REVIEW.md for the assistant's review, rubric, and limits. Automated flags are not correctness scores: the observed answer passes citation integrity but flags Chinese prose for an English question and a missing CliRunner mention. Semantic accuracy and claim support require manual review. No paid API calls were made while adding this evaluator.

## Explicit language and usage-guide scope

```bash
# Offline generation preview; cached local retrieval only:
.venv/bin/python answer.py --preview \
  "How do I test a command and inspect its output?" \
  --retriever hybrid --scope guide --language en --top-k 3

# Optional paid follow-up, preserving the earlier run:
.venv/bin/python answer.py --live --provider deepseek \
  "How do I test a command and inspect its output?" \
  --retriever hybrid --scope guide --language en --top-k 3 \
  --save-run data/answers/onboarding-02.json

python3 quality.py --run data/answers/onboarding-02.json --case answer-01
```

`--language auto` retains the existing question-language instruction. `en` and `zh` explicitly request English or Simplified Chinese claim/limitation prose; quotes, code identifiers and JSON keys remain unchanged. Both provider prompts receive the override. The option is an instruction, not a guarantee of model compliance; the quality checker uses the saved explicit language when present, retaining its heuristic/manual-review limitations. No paid generation was run while adding this feature.

`--scope guide` restricts candidates to Markdown under `docs/` and README.md files at any depth. Use `--docs-root manual` for another layout. It does not identify tutorials automatically and can include reference/changelog material. Non-Markdown documents are not supported by the current index. No fallback to code occurs if there are no eligible matches. Default scope remains `all`.

Scoping uses the existing full-corpus vectors and BM25 statistics. Each retrieval branch is filtered before selecting its top 50 hybrid-fusion candidates, preventing code candidates from crowding out the document candidate pool. This exact scan is suitable for the small local corpus; larger indexes should implement native metadata filtering. No question-specific filename boosts are used.

For the onboarding question above, guide-mode top three are docs/testing.md:66-145, 196-275, and 131-210. The first contains CliRunner import, instantiation, invocation, and output/exit-code assertions. It shows a subcommand example, not necessarily the simplest introduction. Model answer completeness is still unverified until a new live answer is reviewed.

Offline comparison on four existing documentation development questions is saved in evaluation/guide-scope-comparison.json. Labeled evidence ranks (all -> guide): dev-09 missing -> 4; dev-10 missing -> 5; dev-11 missing -> missing; dev-12 3 -> 1. Top-five labeled hits increase from 1/4 to 3/4 in this selected subset; this is not a general benchmark gain, and relevant alternative passages can still be counted as misses.

28 tests pass. Tests cover scope boundaries, custom docs directories, unchanged full-scope behavior/scores, branch filtering before fusion, language propagation, review-language override, and citations ending in a blank source line. The latter fixes a discovered splitlines edge case while preserving original source line ranges. Saved live runs now also record language, scope, docs directory and top-k.

## Citation-generation reliability update

A user-observed guide-mode live call failed exact quote validation; consequently no onboarding-02.json success record existed. The raw rejected response was not retained, so the precise cause (line selection, whitespace, or rewritten quote) cannot be determined from that error alone.

The generation contract now asks the model only for source IDs and inclusive line ranges. Evidence is sent with explicit original line-number prefixes. The application validates the selected range, then extracts the quote verbatim from the indexed source. It does not change the selected range or repair invalid source IDs. Legacy model responses that include quotes still undergo exact matching; incorrect supplied quotes are rejected. Saved answers retain their quotes, so existing offline quality checks continue to work. New run records include citation_policy=source-extracted-v1.

This eliminates reliance on the model copying whitespace and source text correctly. It does NOT establish that the model selected the right evidence or that the evidence supports the claim; those remain review tasks. There are no automatic paid retries. Missing run records now produce a concise quality.py error instead of a traceback.

30 tests pass, including range-only responses from both providers and rejection of invalid ranges, fabricated sources, and incorrect legacy quotes. Live reliability after this update is not yet measured. If onboarding-02.json does not exist, the same previously shown live command and filename can be used for one new paid attempt. Run quality.py only after answer.py confirms that the review record was saved.
