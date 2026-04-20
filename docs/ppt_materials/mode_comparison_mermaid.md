# Mode Comparison Mermaid

```mermaid
flowchart TB
    subgraph N[no_guidance]
        N1[Fixed Pretest] --> N2[State Logged Only] --> N3[Fixed Posttest]
    end

    subgraph G[generic_guidance]
        G1[Fixed Pretest] --> G2[Generic Hint] --> G3[Fixed Practice] --> G4[Fixed Posttest]
    end

    subgraph A[adaptive_guidance]
        A1[Fixed Pretest] --> A2[Learner State] --> A3[Structured Tutor Plan] --> A4[Adaptive Practice + Feedback] --> A5[Fixed Posttest]
    end
```

## PPT Notes

- The pretest and posttest bundles are the same across modes.
- Practice is an intervention and is not included in final `score_delta`.
- Adaptive mode is the only branch where learner state drives the tutoring plan.
