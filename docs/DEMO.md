# Three-minute demo script

[Watch the narrated English walkthrough](https://raw.githubusercontent.com/ychen3751/repolens/main/docs/media/RepoLens-Walkthrough.mp4) · [English subtitles](https://raw.githubusercontent.com/ychen3751/repolens/main/docs/media/RepoLens-English.srt)

Use this longer script for an interview demo. Run from the repository root. Use English narration and keep credentials off screen.

## 0:00–0:30 — Problem and approach
“RepoLens helps developers explore an unfamiliar Python repository. It retrieves source evidence and generates answers with traceable file and line references. I compare retrieval strategies and check citations rather than assuming a fluent answer is correct.”

Show the README architecture diagram. State that this is a CLI prototype and the example corpus is a pinned Click checkout.

## 0:30–1:15 — Evidence before generation
With the corpus already indexed and model cached:

```bash
.venv/bin/python answer.py --preview \
  "How do I test a command and inspect its output?" \
  --retriever hybrid --scope guide --top-k 3
```

Show docs/testing.md and the CliRunner setup. Explain that guide mode is an explicit documentation filter, not automatic intent detection.

## 1:15–2:00 — A real answer and its sources
If a successful run already exists locally, show it rather than paying to regenerate solely for recording. Label it “previously saved live response.” Do not present `--demo` as a live model answer.

```bash
python3 quality.py --run data/answers/onboarding-02.json --case answer-01
```

Show the English claims and source references from the saved run. Explain that quotations are extracted by the application from model-selected ranges, and that citation integrity is separate from claim correctness. The saved file is local and is not part of the release package.

## 2:00–2:40 — Experiments and tradeoffs

```bash
.venv/bin/python compare.py
```

Use cached embeddings. Explain that the 16-question development set is small and assistant-labeled. Semantic and hybrid each reach 9/16 top-five hits, while BM25 performs better at top three. Explain the separate query/document caches and token-safe windows. Do not claim a production speedup from one local timing observation.

## 2:40–3:00 — Limitations and next steps
“Next I would independently review labels, reserve held-out questions, evaluate claim support, and test more repositories. Prompt injection and abstention cases are prepared but not fully evaluated.”

## No-key alternative

```bash
python3 answer.py --demo
python3 quality.py
```

Label these correctly: the first is a synthetic hand-authored fixture; the second reviews a reconstructed user-observed response. Neither makes a live generation API call.
