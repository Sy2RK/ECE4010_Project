# Architecture For PPT

## High-Level Chain

```text
Config + Tasks + Learner Profiles
        |
        v
Pretest
        |
        v
Evaluation + Interaction Records
        |
        v
Learner Modeling
        |
        v
Guidance Branch
   | no guidance
   | generic guidance
   | adaptive guidance
        |
        v
Intermediate Practice
        |
        v
Posttest
        |
        v
Metrics + Cases + Report
```

## Module-Level Explanation

| module | what it does | PPT wording |
| --- | --- | --- |
| Pretest | asks each learner fixed baseline tasks | collects initial ability evidence |
| Evaluation | scores answers and tags errors | converts responses into measurable signals |
| Learner Modeling | updates grammar, vocabulary, reading, confidence | creates explicit learner state |
| Guidance Branch | selects no/generic/adaptive path | defines the controlled experimental condition |
| Practice | runs non-scored intervention tasks | operationalizes the guidance |
| Posttest | asks fixed outcome tasks | measures effect under comparable conditions |
| Metrics / Report | aggregates deltas and cases | provides evidence for presentation |

## What To Avoid In PPT

- Do not show file paths or function names.
- Do not show every artifact type on the main architecture slide.
- Do not describe it as a production tutoring platform.

## Recommended Architecture Slide Caption

The system is an offline experiment loop: pretest responses are converted into learner state, which controls the tutoring intervention before a fixed posttest comparison.
