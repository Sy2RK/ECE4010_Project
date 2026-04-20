# 11-Page PPT Outline

## Slide 1 - Title

Title: Adaptive English AI Tutor: A Controlled Prototype for Personalized Guidance

Subtitle: Learner-state modeling, adaptive practice, and GRU-assisted evaluation in an offline experiment pipeline.

Core goal: evaluate whether explicit learner-state-driven guidance improves English task performance compared with no guidance and generic guidance.

## Slide 2 - Introduction / Motivation

PPT bullets:

- Modern LLMs can explain grammar and answer reading questions.
- But many AI tutor demos are generic: they respond well but do not explicitly track learner state.
- For education, personalization should be evaluated under controlled pre/post comparison.
- This project builds a small but runnable loop to test adaptive guidance, not a full product.

Speaker note: The motivation is not to build another chatbot tutor, but to test whether explicit learner modeling can make tutoring interventions more targeted and measurable.

Visual suggestion: two-column concept diagram, "Generic Tutor: same hint for all" vs "Adaptive Tutor: learner state -> personalized plan".

## Slide 3 - Problem Definition

Main research question:

Can learner-state-driven adaptive guidance improve LLM learner agents' English task performance under a controlled pretest/posttest setup?

Sub-goals:

- Build a runnable offline pipeline with learner agents, evaluation, learner modeling, guidance, practice, and reporting.
- Compare no guidance, generic guidance, and adaptive guidance under the same pre/post task bundles.
- Measure both learning-effect proxy scores and efficiency improvement from GRU judge triage.

## Slide 4 - Existing Methods / Gap

PPT gap bullets:

- Generic LLM tutoring provides useful feedback but often uses the same strategy for different learners.
- Many demos do not expose a structured learner state that drives the next tutoring action.
- Without fixed pre/post bundles, observed improvement can be caused by easier questions rather than better guidance.
- Few lightweight prototypes compare no, generic, and adaptive guidance in one controlled pipeline.

Speaker note: Our contribution is a compact experimental loop: explicit learner state, structured tutor plans, controlled posttest comparison, and artifact-level reporting.

## Slide 5 - System Overview / Main Architecture

PPT flow:

`Pretest -> Learner Modeling -> Guidance Branch -> Practice -> Posttest -> Metrics / Report`

Module summary:

| module | input | output | role |
| --- | --- | --- | --- |
| Pretest | fixed task bundle, learner profile | scored responses | baseline ability evidence |
| Learner Modeling | interactions and error tags | state vector and top errors | exposes current learner state |
| Guidance Branch | mode and learner state | no/generic/adaptive intervention | controls experimental condition |
| Practice | recommended or fixed tasks | scored practice records | non-scored intervention |
| Posttest | fixed task bundle | scored responses | outcome measurement |
| Metrics / Report | all artifacts | tables and cases | supports analysis and presentation |

## Slide 6 - Three Guidance Modes

| mode | learner state used? | practice? | feedback type | score comparison |
| --- | --- | --- | --- | --- |
| no_guidance | logged only | no | none | fixed pre vs fixed post |
| generic_guidance | no | fixed reserve tasks | same generic hint | fixed pre vs fixed post |
| adaptive_guidance | yes | plan-selected tasks | personalized feedback and post-practice summary | fixed pre vs fixed post |

Key point: practice is an intervention, not part of the final score calculation.

## Slide 7 - Learner Modeling + GRU Component

PPT bullets:

- Learner state: grammar, vocabulary, reading, confidence.
- State update uses task scores and recent error tags to identify weakest skill and top errors.
- Adaptive plan uses this state to choose focus skill, difficulty, feedback style, and practice tasks.
- GRU triage is enabled in Reading QA evaluation to skip high-confidence LLM judge calls.
- Latest runs: judge calls reduced from 69 to 12 per run, saving 57 calls.

Short phrasing: The system combines LLM tutoring with local learner-state modeling and a GRU-based evaluation triage module.

## Slide 8 - Dataset + Experimental Design

PPT bullets:

- 20 static English tasks: 10 grammar correction, 10 reading QA.
- Difficulty levels: 8 medium and 12 hard tasks.
- 3 simulated learner agents: overall weak, grammar weak, reading weak.
- Each learner/task type has fixed pretest and posttest bundles.
- Three modes use the same pre/post bundles for fair comparison.

| task type | count | role |
| --- | ---: | --- |
| grammar_correction | 10 | grammar accuracy and error-tag evaluation |
| reading_qa | 10 | evidence extraction and short-answer evaluation |

## Slide 9 - Fairness / Controlled Comparison

PPT bullets:

- Same learner and task type use the same pretest/posttest bundles across all modes.
- Pretest seed is mode-neutral, so baseline answers are controlled.
- Practice is recorded but excluded from `score_delta`.
- Final metric is always `posttest_score - pretest_score`.
- Latest three runs have 0 inconsistent pretest groups across 24 learner/task combinations.

One-sentence summary: The design isolates the effect of guidance by keeping the measurement tasks fixed and excluding practice from the final score.

## Slide 10 - Main Results

Main table:

| mode | avg_pretest | avg_posttest | avg_delta |
| --- | ---: | ---: | ---: |
| no_guidance | 0.719 | 0.697 | -0.022 |
| generic_guidance | 0.719 | 0.821 | 0.102 |
| adaptive_guidance | 0.719 | 0.854 | 0.135 |

PPT conclusion:

- Guidance improves over no guidance.
- Adaptive guidance is strongest in the latest prototype runs.
- Adaptive gains are especially visible on Reading QA.

Chart suggestion: one simple bar chart of `avg_delta by mode`.

## Slide 11 - Conclusion / Limitations / Future Work

PPT bullets:

- Implemented a full offline adaptive tutoring experiment pipeline.
- Adaptive guidance improves over no guidance in controlled runs.
- GRU triage reduces LLM judge calls by 82.61% in Reading QA evaluation.
- Current limitation: results are still small-scale and based on simulated learners.
- Next step: larger validation data and real-user evaluation.

Closing sentence: This prototype demonstrates feasibility: explicit learner state can drive a measurable tutoring loop, while local ML can reduce evaluation cost.

## Slide 12 - Optional Q&A

Likely questions:

- Why use learner agents instead of real users?
- Why does generic guidance outperform adaptive?
- Is GRU replacing the tutor?
- How fair is the pre/post comparison?
