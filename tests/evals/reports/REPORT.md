# RAG Evaluation Report

_Run 2026-07-23T12:49:02.091683+00:00_ · dataset v1.0 · eval_today 2026-06-01 · fixture `1d16c4a67876`

Results are **repeatable-with-variance, not bit-reproducible**: temperature 0 reduces variance but OpenAI is not deterministic. Across runs, routing has ranged 30–31/31 and judge calibration 7–8/8 — read single-run numbers with that in mind.

## Models

| role | model | temperature |
|---|---|---|
| chat (system under test) | gpt-4o-mini | 0.0 (prod 0.2) |
| embedding | text-embedding-3-small | — |
| judge | gpt-4o | 0.0 |

Judge calibration this run: **8/8** agree with the human-graded set (advisory). `system_fingerprint`: not captured.

## Results

| dimension | n | result |
|---|---|---|
| routing | 31 | 30/31 correct, 0 diverged |
| recall@5 | 17 | 0.94 |
| precision@5 | 17 | 0.20 |
| MRR@5 | 17 | 0.91 |
| SQL correctness | 11 | 10/11 |
| must_mention | 19 | 19/19 |
| judge faithfulness | 18 | 5.00 |
| judge relevance | 18 | 4.83 |

_MRR carries rank jitter (score-only ordering); judge scores are advisory, per-dimension — never a single pass/fail._

_See `ANALYSIS.md` for interpretation of these results._
