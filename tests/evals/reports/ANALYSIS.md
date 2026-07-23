# RAG Evaluation — Analysis

This document explains the numbers in [`REPORT.md`](./REPORT.md) and [`results.json`](./results.json).
The harness measures the RAG pipeline on four separate dimensions: routing, retrieval, SQL
correctness, and answer quality. It uses a golden dataset of 31 cases that were checked by hand.
The evaluation date is frozen, so questions with relative dates are reproducible.

## Summary

The pipeline works well on the easy cases and shows problems on the hard ones. Routing is almost
always correct, retrieval finds the right document, and SQL counts are correct except for one
case. The interesting results are the few cases that the fixture was built to test. These are the
cases where the evaluation is useful.

## What works well

- Routing is correct on 30–31 of 31 cases. The case that fails changes between runs (see Variance).
- Recall@5 is 1.00 on almost every case, so the target document is almost always in the top 5.
  But with only 15 documents this is an easy result, so recall does not show differences well.
  MRR is a better signal for retrieval.
- SQL correctness is 10 of 11. The counts are exact when routing and filter extraction are correct.

A note about precision@5 (about 0.20): this is not a weakness, it is math. Each case has only one
relevant chunk, and we retrieve 5, so precision cannot be higher than 0.2. It is shown for
completeness. Recall and MRR are the real retrieval signals here.

## Findings

### 1. "Opened in the last N days" is read as a status filter

The question "how many tickets were opened in the last 7 days?" uses the word "opened". The
classifier reads this as a filter `status = open` and adds it to the date window. This drops the
in-progress tickets and returns 2 instead of 3. The date window itself is correct. The problem is
the extra status filter that comes from the verb. The fix is a small change in the prompt: verbs
like "opened" or "created" mean the creation date, not a status. This is tracked as follow-up work.

### 2. Ambiguous question: retrieval rank and the judge agree

For the question "all remote employees suddenly cannot connect", the FAQ document is ranked higher
than the certificate-renewal runbook (reciprocal rank about 0.5). The judge also gives a lower
relevance score. Two different dimensions point to the same case, which is a strong signal. But the
question is really ambiguous: the FAQ does describe this situation and points to the runbook. So
this is probably an incomplete relevance label, not a retrieval bug. It needs a human decision, not
a change to make the number look better.

### 3. Retrieval is perfect, but the answer is incomplete

This is the clearest example of why the judge is needed. For the certificate-policy question,
retrieval is perfect (recall and MRR = 1.0). But the answer does not include the SEV-2 escalation
detail that is in the reference answer. No retrieval metric can see this. Only the judge can, and it
names the missing detail. This is a normal loss from summarization, so it is advisory, not a
separate bug.

### 4. Unstable routing

The question "requests-per-minute limits per tier" is on the border between the SQL route and the
documentation route (the word "limits" looks like a number question). Between runs, the route
changes. When it goes to the SQL route, routing, retrieval, and the answer all fail together. This
is the clearest example of why the results are reported with variance, and why the four dimensions
are scored separately. The chain of failures is visible, not hidden inside one number.

## Variance

All numbers here are repeatable with variance, not bit-reproducible. Temperature 0 reduces the
variance, but the models are not deterministic. Between runs, with the same code and the same
fixture, routing was 30–31 of 31 and the judge calibration was 7–8 of 8. So one run is not a final
result. The report records the three models, the dataset version, and the frozen evaluation date,
so two runs can be compared. Unstable cases (finding 4) are shown clearly.

The judge is advisory. Before each run it is checked against a small set of answers that a human
graded. It is reported per dimension and is never turned into one pass/fail result. The judge
changes by one item between runs (7–8 of 8), which is normal for an LLM. This is why it is advisory
and not a gate.
