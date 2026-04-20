# Cases For PPT

## Case 1 - Adaptive Success: Learner A / Reading QA

Why show it: clean example where learner-state-driven guidance beats the generic baseline without changing the fixed posttest.

| item | content |
| --- | --- |
| learner | `learner_a`, overall weak |
| task type | Reading QA |
| mode | adaptive_guidance |
| pretest -> posttest | 0.46 -> 0.853 |
| delta | +0.393 |
| learner state | weakest skill: reading; top errors: low keyword overlap, missing key evidence |
| tutor plan | focus on reading, keyword identification, evidence extraction |
| practice | `r9`, `r4`; scores 0.5 and 1.0 |

PPT message: Adaptive guidance used the same general reading checklist idea, but added personalized focus on missing evidence and concrete reasons. This produced the strongest improvement for this learner-task pair.

## Case 2 - Controlled Comparison: Same Baseline, Different Interventions

Why show it: demonstrates fairness and why the adaptive gain is interpretable.

Learner: `learner_a`, task type: Reading QA.

| mode | pretest | posttest | delta |
| --- | ---: | ---: | ---: |
| no_guidance | 0.46 | 0.375 | -0.085 |
| generic_guidance | 0.46 | 0.750 | +0.290 |
| adaptive_guidance | 0.46 | 0.853 | +0.393 |

PPT message: Same learner, same pretest bundle, same posttest bundle. Only the intermediate intervention changes, so the adaptive improvement is not caused by easier posttest items.

## Case 3 - Honest Boundary Case: Learner B / Reading QA

Why show it: keeps the conclusion non-overclaimed.

| item | content |
| --- | --- |
| learner | `learner_b`, grammar-weak profile |
| task type | Reading QA |
| generic delta | +0.130 |
| adaptive delta | +0.102 |
| interpretation | adaptive was positive but did not beat generic for this specific learner-task pair |

PPT message: Adaptive is best on average in the latest runs, but not every subcase is a win. This supports a careful claim: the current adaptive strategy is promising and measurable, not universally proven.
