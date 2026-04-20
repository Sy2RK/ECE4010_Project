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
| adaptive_guidance | 0.135 |

GRU triage reduced Reading QA judge calls from 69 to 12 per run, saving 57 calls, or 82.61%.

## Safest Presentation Claim

The prototype demonstrates a complete adaptive tutoring loop. In the latest controlled API runs, adaptive guidance outperforms both no guidance and generic guidance, with the strongest gain on Reading QA. This should still be presented as prototype-scale evidence, not a broad educational claim.

## 5-Minute Narrative

1. AI tutors can answer and explain, but often lack explicit learner-state tracking.
2. We define a controlled adaptive tutoring experiment instead of a full product.
3. The system models learner state after pretest, generates adaptive plans, runs practice, then compares fixed posttest results.
4. Results show guidance helps; adaptive guidance is positive versus no guidance.
5. GRU triage adds a local ML component that reduces expensive LLM judge calls.
6. Limitations remain: small task set, simulated learners, and prototype-scale validation.
