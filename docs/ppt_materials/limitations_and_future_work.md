# Limitations And Future Work

## Limitations

- Learners are simulated LLM agents, not real students.
- Dataset is intentionally small: 20 tasks total.
- Generic guidance currently outperforms adaptive guidance overall.
- Adaptive planning uses one intermediate practice phase only; no long-term learning history.
- GRU triage is trained on a small internal sample and needs broader validation.
- Results support feasibility, not educational efficacy.

## Future Work

- Improve adaptive post-practice replanning instead of using only the initial plan.
- Expand task bank and include more difficulty levels.
- Validate GRU triage on larger shadow-mode data before stronger claims.
- Add stronger personalization features: error-specific mini-lessons, task sequencing, and memory across sessions.
- Evaluate with real students or human-written learner simulations.

## PPT Closing Version

The prototype is feasible and measurable, but current results are best interpreted as a controlled proof of concept. The next technical challenge is making adaptive guidance stronger than a simple generic baseline.
