# Source-only BM25 failure analysis

Development set only. No retrieval rules or labels changed in this step.
Reproduce from the repolens directory: `python3 diagnose.py`.
Machine-readable observations: `bm25-misses.json`.

## dev-01: Group command resolution
The first evidence-containing chunk is ranked 40, at src/click/core.py:2081-2160.
It matches only `command` from the tokenized query. `resolution` is not normalized to `resolve`, and `implemented` is absent. The containing class is defined at line 1703, so the fixed window also loses the enclosing `Group` identity.
The top result matches `command` and `implemented`. A different, irrelevant chunk ranks second because it contains `resolution` in comments about filesystem timestamp precision. Lexical matches do not distinguish those meanings.

## dev-06: styled output
The first evidence-containing chunk is ranked 37, at src/click/termui.py:781-860.
The actual secho function starts at line 780 and ends at 811. The chunk containing its implementation starts one line after its function name. The first-ranked chunk (716-795) includes that function name and part of its documentation, but stops before the implementation at 808-811.
The first-ranked chunk also includes neighboring style/unstyle content. It is related to the question, but does not cover the labeled implementation evidence. The implementation chunk matches `echo` and `with`; `combine`/`combines`, `styling`/`style`, and `colored`/`color` are not normalized by the baseline.

## Interpretation and next experiment
Observed: fixed windows can separate a symbol name or enclosing class from its implementation, while exact tokens reward incidental matches. These observations suggest causes; they do not establish how much each cause contributes.
Next experiment: add optional Python syntax-aware function/method chunks with enclosing-class metadata. Preserve exact source line ranges and use the same query set and source-only mode. Keep the existing fixed-window baseline for comparison. Do not simultaneously change token normalization or embeddings: measure the chunking change first. Long functions will still need a size bound and a documented splitting policy.

This diagnostic ranks all matching source candidates, not just the top five. A missing target in this report means no positive-scoring evidence match; it is not proof the repository lacks an answer. Labels are assistant-reviewed and user review remains pending. No generalization or answer-accuracy claim follows from eight development questions.
