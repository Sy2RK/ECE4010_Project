# GRU Summary For PPT

## PPT Short Version

The project includes a local PyTorch GRU triage model in the Reading QA evaluation path. It predicts whether a gray-zone reading answer can safely skip the LLM judge. In the latest default runs, it reduced judge calls from 71 to 15 per run, saving 56 calls or 78.87%.

## Where GRU Sits

```text
Reading QA answer
      |
Rule-based overlap / evidence score
      |
Gray-zone answer?
      |
GRU triage
      | high confidence -> use triage score, skip LLM judge
      | low confidence  -> call LLM judge
```

## What It Uses

The GRU does not read raw passages directly. It consumes structured feature sequences:

- component overlap
- keyword ratio
- evidence coverage
- answer/reference length ratio
- task difficulty
- answer length
- component length
- component position

## Latest Efficiency Result

| metric | value |
| --- | ---: |
| triage candidates | 71 |
| GRU predictions | 71 |
| judge calls after GRU | 15 |
| skipped judge calls | 56 |
| judge-call reduction | 78.87% |

## Accurate Claim

Safe PPT claim: GRU triage improves evaluation efficiency by reducing LLM judge calls in the current prototype.

Do not overclaim: The GRU is not the main tutoring intelligence and is not yet validated on a large external dataset.

## If Asked In Q&A

The core adaptive tutoring loop is driven by learner-state modeling and tutor planning. The GRU is an auxiliary machine intelligence component for efficiency: it replaces some expensive LLM judge calls when confidence is high. If the checkpoint is missing or confidence is low, the system falls back to the LLM judge.

## Two Possible Presentation Positions

### A. Since GRU results are completed

Use it as one slide-level technical highlight: "Local GRU triage reduces judge calls by 78.87% while preserving fallback behavior."

### B. Conservative fallback wording

"The GRU path is enabled as a neural enhancement for evaluation efficiency; current results are promising, but larger validation is future work."
