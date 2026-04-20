# Results Analysis

## Data Used

Latest current-chain runs with GRU triage enabled:

- `outputs/sample_api_run_23`
- `outputs/sample_api_run_24`
- `outputs/sample_api_run_25`

The three runs produced identical aggregate results.

## Main Findings

### 1. Which mode is currently best?

`generic_guidance` is currently best overall.

| mode | avg_delta |
| --- | ---: |
| generic_guidance | 0.102 |
| adaptive_guidance | 0.061 |
| no_guidance | -0.022 |

### 2. Is adaptive better than no guidance?

Yes. Adaptive guidance improves by `+0.061`, while no guidance decreases by `-0.022`.

PPT-safe claim: adaptive guidance is positive and clearly better than no guidance in this prototype.

### 3. Is adaptive better than generic guidance?

No. Generic guidance is higher overall: `+0.102` vs `+0.061`.

PPT-safe claim: adaptive guidance works as a personalized closed loop, but it is not yet better than a strong generic baseline.

### 4. What conclusion can be stated strongly?

- The system is runnable end-to-end.
- Guidance improves over no guidance.
- Adaptive guidance improves over no guidance.
- GRU triage reduces Reading QA judge calls by 78.87%.
- Reading QA benefits more from guidance than grammar correction in this setup.

### 5. What conclusion should be stated cautiously?

- Adaptive personalization is promising, but not yet the strongest condition.
- The current task set is small, so results show feasibility rather than general educational effectiveness.
- Learner agents are simulated, not real students.

### 6. What must not be said?

- Do not say adaptive guidance is proven best.
- Do not say the system is a complete education product.
- Do not say GRU is the core tutor model.
- Do not claim real student learning improvement.
- Do not claim large-scale statistical significance.

## Most Stable PPT Conclusion

The prototype demonstrates a controlled adaptive tutoring loop. In current API experiments, adaptive guidance improves over no guidance, and the GRU component substantially reduces judge API calls. However, generic guidance remains stronger overall, so future work should improve adaptive planning and post-practice replanning.

## Suggested Result Visualization

Use one bar chart: `avg_delta by mode`.

Optional second chart only if space permits: grouped bars for `grammar_delta` and `reading_delta` by mode.
