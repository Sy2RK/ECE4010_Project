# Architecture Mermaid

Use this as a PPT drawing reference, not necessarily as raw slide text.

```mermaid
flowchart LR
    A[Config + Tasks + Learner Profiles] --> B[Pretest]
    B --> C[Evaluation + Error Tags]
    C --> D[Learner Modeling]
    D --> E{Guidance Mode}
    E -->|No Guidance| F1[No Intervention]
    E -->|Generic Guidance| F2[Generic Hint + Fixed Practice]
    E -->|Adaptive Guidance| F3[Tutor Plan + Personalized Feedback + Adaptive Practice]
    F1 --> G[Posttest]
    F2 --> G
    F3 --> G
    G --> H[Metrics + Cases + Report]
```

## Slide Caption

The prototype turns learner responses into learner state, uses the state to control the tutoring intervention, and evaluates outcomes on fixed posttest tasks.
