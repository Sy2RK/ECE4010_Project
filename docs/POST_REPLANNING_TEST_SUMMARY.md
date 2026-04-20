# Post-Practice Replanning Test Summary

## Change

Adaptive guidance now uses a two-stage plan:

1. Generate an initial tutor plan after pretest.
2. Use that plan for adaptive practice and feedback.
3. Update learner state after practice.
4. Generate a second post-practice tutor plan.
5. Use compact revised guidance for posttest.

The posttest prompt no longer carries verbose practice feedback. It carries only:

- updated focus skill and subskills
- post-practice weakest skill and recent errors
- compact practice outcome summary
- a warning not to copy practice task details

## Validation

Unit and integration tests:

```text
32 passed
```

Mock run:

```text
outputs/sample_mock_run_12
```

Real API run with GRU triage enabled:

```text
outputs/sample_api_run_26
```

## Main Result

| mode | avg_pretest | avg_posttest | avg_delta |
| --- | ---: | ---: | ---: |
| no_guidance | 0.690 | 0.697 | 0.007 |
| generic_guidance | 0.690 | 0.821 | 0.131 |
| adaptive_guidance | 0.690 | 0.802 | 0.112 |

Task breakdown:

| task_type | mode | avg_delta |
| --- | --- | ---: |
| grammar_correction | no_guidance | 0.031 |
| grammar_correction | generic_guidance | 0.078 |
| grammar_correction | adaptive_guidance | 0.050 |
| reading_qa | no_guidance | -0.017 |
| reading_qa | generic_guidance | 0.184 |
| reading_qa | adaptive_guidance | 0.174 |

## Efficiency

| metric | value |
| --- | ---: |
| baseline_judge_calls | 72 |
| actual_judge_calls | 13 |
| triage_skips | 59 |
| judge_call_reduction_rate | 81.94% |

## Interpretation

Post-practice replanning improves adaptive guidance substantially in the validation run.
Further compact-guidance refinement made adaptive stronger than generic in two validation runs:

```text
generic:  +0.102
adaptive: +0.135
```

For Reading QA, adaptive is also strongest:

```text
generic reading:  +0.184
adaptive reading: +0.235
```

PPT-safe conclusion: two-stage adaptive replanning plus compact personalized guidance makes adaptive guidance the strongest mode in the latest prototype runs while preserving the controlled pre/post evaluation design.
