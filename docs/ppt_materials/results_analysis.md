# Results Analysis

## Data Used

Latest current-chain runs with GRU triage, post-practice replanning, and compact adaptive guidance:

- `outputs/sample_api_run_29`
- `outputs/sample_api_run_30`

The two validation runs produced stable aggregate ordering: adaptive > generic > no guidance.

## Main Findings

### 1. Which mode is currently best?

`adaptive_guidance` is currently best overall in the latest validation runs.

| mode | avg_delta |
| --- | ---: |
| adaptive_guidance | 0.135 |
| generic_guidance | 0.102 |
| no_guidance | -0.022 |

### 2. Is adaptive better than no guidance?

Yes. Adaptive guidance improves by `+0.135`, while no guidance decreases by `-0.022`.

PPT-safe claim: adaptive guidance is positive and clearly better than no guidance in this prototype.

### 3. Is adaptive better than generic guidance?

Yes in the latest validation runs: adaptive is `+0.135`, while generic is `+0.102`.

PPT-safe claim: after adding post-practice replanning and compact personalized guidance, adaptive guidance outperforms the generic baseline in this prototype.

### 4. What conclusion can be stated strongly?

- The system is runnable end-to-end.
- Guidance improves over no guidance.
- Adaptive guidance improves over no guidance and generic guidance in the latest validation runs.
- GRU triage reduces Reading QA judge calls by 82.61% in the latest runs.
- Reading QA benefits more from guidance than grammar correction in this setup.

### 5. What conclusion should be stated cautiously?

- The current task set is small, so results show feasibility rather than general educational effectiveness.
- Learner agents are simulated, not real students.
- Adaptive superiority should be scoped to the current prototype, task set, and model configuration.

### 6. What must not be said?

- Do not say adaptive guidance is universally proven best.
- Do not say the system is a complete education product.
- Do not say GRU is the core tutor model.
- Do not claim real student learning improvement.
- Do not claim large-scale statistical significance.

## Most Stable PPT Conclusion

The prototype demonstrates a controlled adaptive tutoring loop. In the latest API experiments, adaptive guidance improves over both no guidance and generic guidance, while the GRU component substantially reduces judge API calls. The claim should remain scoped to this small prototype and simulated learner setup.

## Suggested Result Visualization

Use one bar chart: `avg_delta by mode`.

Optional second chart only if space permits: grouped bars for `grammar_delta` and `reading_delta` by mode.
