# Limitations And Future Work

## Limitations

- Learners are simulated LLM agents, not real students.
- Dataset is intentionally small: 20 tasks total.
- Adaptive currently outperforms generic in the latest runs, but the margin is prototype-scale and should be validated further.
- Adaptive planning uses one intermediate practice phase only; no long-term learning history.
- GRU triage is trained on a small internal sample and needs broader validation.
- Results support feasibility, not educational efficacy.

## Future Work

- Validate adaptive post-practice replanning across more runs and task variants.
- Expand task bank and include more difficulty levels.
- Validate GRU triage on larger shadow-mode data before stronger claims.
- Add stronger personalization features: error-specific mini-lessons, task sequencing, and memory across sessions.
- Evaluate with real students or human-written learner simulations.

## PPT Closing Version

The prototype is feasible and measurable, but current results are best interpreted as a controlled proof of concept. The next technical challenge is validating adaptive guidance beyond the current small task set and simulated learners.
