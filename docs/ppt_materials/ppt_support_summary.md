# PPT Support Summary

## Project Positioning

This is a lightweight offline prototype for evaluating adaptive English tutoring, not a full online education product.

Core pipeline:

`Pretest -> Learner Modeling -> Guidance Branch -> Practice -> Posttest -> Metrics / Report`

## One-Sentence Pitch

We build a controlled offline experiment pipeline to test whether explicit learner-state modeling and personalized tutoring guidance can improve LLM learner agents' English task performance.

## What Is Already Implemented

- Two English task types: Grammar Correction and Reading QA.
- Three learner agents with different weakness profiles.
- Three guidance modes: no guidance, generic guidance, adaptive guidance.
- Fixed pretest/posttest bundles for controlled comparison.
- Intermediate practice phase for generic/adaptive modes only.
- Learner state modeling with grammar, vocabulary, reading, and confidence dimensions.
- OpenAI-compatible API backend plus mock backend.
- GRU-based Reading QA judge triage enabled by default to reduce LLM judge calls.
- Run artifacts: interactions, states, plans, feedback, metrics, cases, reports.

## Latest Main Results

| mode | avg_delta |
| --- | ---: |
| no_guidance | -0.022 |
| generic_guidance | 0.102 |
| adaptive_guidance | 0.061 |

GRU triage reduced Reading QA judge calls from 71 to 15 per run, saving 56 calls, or 78.87%.

## Safest Presentation Claim

The prototype demonstrates a complete adaptive tutoring loop and shows that adaptive guidance improves over no guidance in controlled API experiments. However, generic guidance currently performs better overall, so adaptive guidance should not be claimed as the best method yet.

## 5-Minute Narrative

1. AI tutors can answer and explain, but often lack explicit learner-state tracking.
2. We define a controlled adaptive tutoring experiment instead of a full product.
3. The system models learner state after pretest, generates adaptive plans, runs practice, then compares fixed posttest results.
4. Results show guidance helps; adaptive guidance is positive versus no guidance.
5. GRU triage adds a local ML component that reduces expensive LLM judge calls.
6. Limitations remain: small task set, simulated learners, and generic guidance is still stronger overall.
