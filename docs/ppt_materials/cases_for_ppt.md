# Cases For PPT

## Case 1 - Adaptive Success: Learner A / Reading QA

Why show it: clean example of learner-state-driven personalization.

| item | content |
| --- | --- |
| learner | `learner_a`, overall weak |
| task type | Reading QA |
| mode | adaptive_guidance |
| pretest -> posttest | 0.46 -> 0.625 |
| delta | +0.165 |
| learner state | weakest skill: reading; top errors: low keyword overlap, missing key evidence |
| tutor plan | focus on reading, keyword identification, evidence extraction |
| practice | `r9`, `r4`; scores 0.5 and 1.0 |

PPT message: Adaptive guidance identified reading evidence extraction as the main weakness and produced a positive posttest gain.

## Case 2 - Generic Stronger: Learner A / Reading QA

Why show it: keeps the conclusion honest.

| item | content |
| --- | --- |
| learner | `learner_a` |
| task type | Reading QA |
| mode | generic_guidance |
| pretest -> posttest | 0.46 -> 0.75 |
| delta | +0.29 |
| intervention | fixed generic reading checklist and fixed practice tasks |

PPT message: A simple generic checklist is a strong baseline. Current adaptive guidance works, but is not yet superior to generic guidance.

## Case 3 - Controlled Comparison: Same Baseline, Different Interventions

Why show it: demonstrates fairness and experimental design.

Learner: `learner_a`, task type: Reading QA.

| mode | pretest | posttest | delta |
| --- | ---: | ---: | ---: |
| no_guidance | 0.46 | 0.375 | -0.085 |
| generic_guidance | 0.46 | 0.75 | +0.29 |
| adaptive_guidance | 0.46 | 0.625 | +0.165 |

PPT message: Same baseline and same fixed posttest make the intervention comparison interpretable.
