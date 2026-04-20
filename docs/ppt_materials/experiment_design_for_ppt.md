# Experiment Design For PPT

## Goal

Compare whether guidance conditions improve learner-agent performance from pretest to posttest.

## Conditions

| mode | description | intervention |
| --- | --- | --- |
| no_guidance | baseline condition | no feedback or practice |
| generic_guidance | non-adaptive baseline | same hint and fixed practice |
| adaptive_guidance | personalized condition | learner-state-based plan, feedback, practice |

## Dataset

| task type | count | pretest bundle | posttest bundle | reserve practice |
| --- | ---: | --- | --- | --- |
| grammar_correction | 10 | 4 tasks | 4 tasks | 2 tasks |
| reading_qa | 10 | 4 tasks | 4 tasks | 2 tasks |

Difficulty distribution: 8 medium tasks and 12 hard tasks.

## Learner Agents

| learner | profile |
| --- | --- |
| learner_a | overall weak: grammar, reading, vocabulary |
| learner_b | weak in grammar |
| learner_c | weak in reading |

## Metric

`score_delta = average_posttest_score - average_pretest_score`

Practice scores are recorded for analysis but excluded from final delta.

## Fairness Controls

- Same learner/task type uses same pretest and posttest bundles across modes.
- Pretest seed is mode-neutral.
- All modes are evaluated with the same scoring module.
- Latest runs: 168 interactions per run and 0 inconsistent pretest groups.

## Speaker Note

This design is intentionally small but controlled. It is suitable for testing the pipeline's feasibility, not for making broad educational claims.
