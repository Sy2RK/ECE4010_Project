# Three-Run API Experiment Summary

Generated from:
- `outputs/sample_api_run_20`
- `outputs/sample_api_run_21`
- `outputs/sample_api_run_22`

## Executive Summary

Across 3 real API runs, adaptive guidance improved scores by **0.054** on average, no guidance changed by **-0.022**, and generic guidance improved by **0.091**.
Adaptive guidance is consistently better than no guidance in these runs, while generic guidance remains slightly higher overall.

## Overall By Mode

| mode | avg_round1 | avg_round2 | avg_delta | delta_sd |
| --- | ---: | ---: | ---: | ---: |
| adaptive_guidance | 0.719 | 0.773 | 0.054 | 0.105 |
| generic_guidance | 0.709 | 0.800 | 0.091 | 0.103 |
| no_guidance | 0.719 | 0.697 | -0.022 | 0.042 |

## Per-Run Overall

| run | mode | avg_round1 | avg_round2 | avg_delta |
| --- | --- | ---: | ---: | ---: |
| sample_api_run_20 | adaptive_guidance | 0.719 | 0.780 | 0.061 |
| sample_api_run_20 | generic_guidance | 0.719 | 0.800 | 0.081 |
| sample_api_run_20 | no_guidance | 0.719 | 0.697 | -0.022 |
| sample_api_run_21 | adaptive_guidance | 0.719 | 0.759 | 0.040 |
| sample_api_run_21 | generic_guidance | 0.719 | 0.800 | 0.081 |
| sample_api_run_21 | no_guidance | 0.719 | 0.697 | -0.022 |
| sample_api_run_22 | adaptive_guidance | 0.719 | 0.780 | 0.061 |
| sample_api_run_22 | generic_guidance | 0.690 | 0.800 | 0.111 |
| sample_api_run_22 | no_guidance | 0.719 | 0.697 | -0.022 |

## By Task Type And Mode

| task_type | mode | avg_round1 | avg_round2 | avg_delta | delta_sd |
| --- | --- | ---: | ---: | ---: | ---: |
| grammar_correction | adaptive_guidance | 0.796 | 0.792 | -0.004 | 0.114 |
| grammar_correction | generic_guidance | 0.777 | 0.816 | 0.039 | 0.127 |
| grammar_correction | no_guidance | 0.796 | 0.769 | -0.027 | 0.032 |
| reading_qa | adaptive_guidance | 0.642 | 0.753 | 0.111 | 0.056 |
| reading_qa | generic_guidance | 0.642 | 0.784 | 0.143 | 0.017 |
| reading_qa | no_guidance | 0.642 | 0.625 | -0.017 | 0.052 |

## By Learner And Mode

| learner_id | no_guidance_delta | generic_guidance_delta | adaptive_guidance_delta |
| --- | ---: | ---: | ---: |
| learner_a | -0.038 | 0.073 | 0.073 |
| learner_b | -0.019 | 0.038 | -0.014 |
| learner_c | -0.010 | 0.163 | 0.102 |

## Artifact And Fairness Checks

| run | interactions | pretest_groups | inconsistent_pretest_groups | judge_calls | triage_skips |
| --- | ---: | ---: | ---: | ---: | ---: |
| sample_api_run_20 | 168 | 24 | 0 | 71 | 0 |
| sample_api_run_21 | 168 | 24 | 0 | 71 | 0 |
| sample_api_run_22 | 168 | 24 | 1 | 71 | 0 |

Notes:
- Each run produced 168 interactions: pretest and posttest for all modes, plus practice interactions for generic/adaptive modes only.
- ``sample_api_run_20`` and ``sample_api_run_21`` had fully consistent pretest responses across modes. ``sample_api_run_22`` had one provider-level nondeterministic pretest item despite mode-neutral seed; this is a real API reproducibility limitation, not a runner prompt difference.
- Reading judge triage was disabled in this config, so ``triage_skips`` is zero.

## Representative Adaptive Cases

| run | learner | task_type | delta | tutor_focus | practice_tasks |
| --- | --- | --- | ---: | --- | --- |
| sample_api_run_22 | learner_a | reading_qa | 0.165 | reading | r9, r4 |
| sample_api_run_21 | learner_a | reading_qa | 0.165 | reading | r9, r4 |
| sample_api_run_20 | learner_a | reading_qa | 0.165 | reading | r9, r4 |
| sample_api_run_22 | learner_c | grammar_correction | 0.135 | grammar | g7, g1 |
| sample_api_run_21 | learner_c | grammar_correction | 0.135 | grammar | g7, g1 |
| sample_api_run_20 | learner_c | grammar_correction | 0.135 | grammar | g7, g1 |

## Interpretation For Presentation

- The current system is architecture-report ready: it demonstrates a complete adaptive tutoring pipeline, persistent learner state, structured tutor planning, intermediate practice, and reproducible artifacts.
- The strongest empirical claim supported by these three runs is: guidance improves over no guidance; adaptive guidance is positive and better than no guidance, especially on Reading QA.
- A cautious claim is needed for adaptive vs generic: generic is still slightly higher on aggregate in this batch, so adaptive should be presented as a functioning personalized closed loop rather than a statistically proven winner.
- If the final presentation requires adaptive to exceed generic, the next engineering target should be stronger post-practice replanning or model-side prompt compression, not more reporting.
