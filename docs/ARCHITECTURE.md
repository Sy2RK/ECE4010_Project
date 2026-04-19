# Adaptive English AI Tutor Architecture

## 1. Overview

This project is a lightweight offline experiment system for evaluating adaptive tutoring on English learning tasks.

The system runs the same learner agents under three guidance modes:

- `no_guidance`
- `generic_guidance`
- `adaptive_guidance`

It currently supports two task types:

- `grammar_correction`
- `reading_qa`

The implementation goal is not a production tutoring platform. It is a reproducible experiment runner that can:

- simulate learner behavior with LLM-based learner agents
- score pretest and posttest answers
- maintain an explicit learner state
- generate a structured tutoring plan
- produce human-readable reports and case studies

## 2. Top-Level Structure

```text
src/adaptive_tutor/
  cli.py
  runner.py
  schemas.py
  io_utils.py
  evaluation.py
  modeling.py
  planning.py
  feedback.py
  next_task.py
  reporting.py
  triage.py
  triage_training.py
  prompts.py
  utils.py
  backends/
    base.py
    mock_backend.py
    openai_backend.py

data/
  config.sample.yaml
  config.mock.yaml
  learners.json
  tasks.jsonl
  bundles.json

outputs/
  <run directories>

tests/
  test_*.py
```

## 3. Runtime Flow

The main runtime path is:

1. CLI parses the command.
2. Config and dataset files are loaded.
3. `ExperimentRunner` iterates over learners, modes, and task types.
4. Pretest tasks are answered by learner agents.
5. Answers are scored.
6. Interaction history updates learner state.
7. In adaptive mode, the system generates a tutoring plan, feedback, and next-task recommendations.
8. Posttest tasks are answered and scored.
9. Metrics, cases, and reports are written to a run directory.

The two CLI entry points are:

- `python -m adaptive_tutor run-experiment --config <path>`
- `python -m adaptive_tutor generate-report --run-dir <path>`
- `python -m adaptive_tutor train-reading-triage --runs <run-dir...> --model-path <path>`

## 4. Core Modules

### `cli.py`

Provides the command-line interface and dispatches to:

- `run_experiment`
- `generate_report`

### `runner.py`

This is the orchestration layer of the project.

Responsibilities:

- load tasks, learners, bundles, and config
- create the selected backend
- run `pretest -> score -> model -> plan/feedback -> posttest -> summarize`
- keep guidance-mode behavior consistent
- write all run artifacts

This file defines the actual experiment contract.

### `schemas.py`

Contains all major Pydantic models used across the project, including:

- task definitions
- learner profiles
- bundle assignments
- config schema
- evaluation result
- learner state
- tutoring plan
- interaction / state / plan / feedback / metric records

This file is the main schema boundary for the system.

### `io_utils.py`

Handles configuration and file I/O.

Responsibilities:

- load YAML / JSON / JSONL / CSV
- resolve relative paths from config location
- expand environment variables in YAML
- read `.env` values for config placeholders
- write run artifacts

### `backends/base.py`

Defines the common backend interface:

- `generate(messages, model, response_format, seed, metadata)`

This keeps the rest of the system backend-agnostic.

### `backends/mock_backend.py`

Implements a deterministic mock backend for offline demos and integration testing.

Responsibilities:

- produce learner answers without real API calls
- generate mock tutoring plans
- generate mock feedback
- generate mock judge results

### `backends/openai_backend.py`

Implements the real OpenAI-compatible API path.

Current use case:

- DashScope-compatible `chat.completions`

Responsibilities:

- initialize the API client
- send chat completion requests
- retry transient provider failures with exponential backoff
- support JSON responses when needed
- pass provider-specific compatibility options

### `evaluation.py`

Implements scoring logic.

Grammar scoring:

- normalized exact match
- partial score from similarity
- grammar error tag detection

Reading scoring:

- exact match
- keyword overlap
- evidence coverage check
- optional local PyTorch GRU triage for judge-call reduction
- optional judge-model reranking for partial answers

This module is the current evaluation bottleneck for experiment quality.

### `triage.py`

Implements the local Reading QA judge triage model.

Responsibilities:

- extract structured evidence-overlap feature sequences
- load a PyTorch GRU checkpoint
- predict the judge score bucket `0.0 / 0.5 / 1.0`
- skip the LLM judge only in `enforce` mode with high confidence

### `triage_training.py`

Trains the GRU triage model from `triage_training.jsonl` rows emitted by prior runs.

It writes:

- `models/reading_judge_triage.pt`
- `models/reading_judge_triage.metrics.json`

Runtime checkpoint loading uses PyTorch `weights_only=True` when available and
validates the checkpoint schema before loading the state dict.

### `modeling.py`

Maintains learner state using a lightweight heuristic temporal updater.

Tracked dimensions:

- `grammar`
- `vocabulary`
- `reading`
- `confidence`

The model updates from:

- item score
- task type
- repeated error penalties
- recent error history

### `planning.py`

Builds the adaptive tutoring plan from learner state.

Responsibilities:

- call the tutor model
- validate the returned JSON plan
- fall back to a heuristic plan if model output is invalid

### `feedback.py`

Generates per-item adaptive feedback records from:

- task
- learner answer
- reference answer
- evaluation result
- tutoring plan

### `next_task.py`

Selects recommended practice tasks based on:

- task type
- target difficulty
- focus skill / subskills
- excluded task IDs

In v1, recommended tasks are recorded but not included in the scored comparison.

### `reporting.py`

Builds human-readable summaries from run artifacts.

Outputs:

- aggregated mode comparison
- learner-level comparison
- task-type comparison
- typical cases

### `prompts.py`

Centralizes prompt construction for:

- learner agents
- tutor planner
- feedback generation
- judge scoring
- generic guidance
- adaptive guidance

This is the prompt policy layer of the project.

## 5. Data Model

### Tasks

Stored in `data/tasks.jsonl`.

Two task schemas are supported.

Grammar correction:

- `task_id`
- `task_type`
- `difficulty`
- `prompt`
- `input_text`
- `reference_answer`
- `skill_tags`

Reading QA:

- `task_id`
- `task_type`
- `difficulty`
- `passage`
- `question`
- `reference_answer`
- `skill_tags`

### Learners

Stored in `data/learners.json`.

Each learner includes:

- `learner_id`
- `weak_skills`
- `mid_skills`
- `strong_skills`
- `typical_errors`
- `answer_style`
- optional `model_id_override`

### Bundles

Stored in `data/bundles.json`.

The bundle file defines:

- named task bundles
- learner-specific mapping from task type to pretest / posttest bundle

The system enforces:

- every bundle reference must exist
- pretest and posttest bundles must not overlap
- every learner must have assignments for every supported task type
- bundles must be non-empty
- bundle task IDs must match the assigned task type

## 6. Configuration Model

Primary config lives in YAML.

Current files:

- `data/config.sample.yaml`: real API mode
- `data/config.mock.yaml`: mock mode
- `data/config.triage.yaml`: API mode with reading judge triage enabled

Config includes:

- backend type and API settings
- model IDs
- learner-specific model overrides
- dataset paths
- output path
- random seed
- enabled guidance modes
- judge gray zone
- intermediate practice settings
- optional reading judge triage settings

Environment variables can be injected into YAML using `${VAR}` or `${VAR:-default}` syntax.

### Learner model resolution order

The learner model used at runtime is resolved in this order:

1. `models.learner_model_overrides.<learner_id>`
2. `learners.json -> model_id_override`
3. `models.shared_learner_model`

## 7. Guidance Modes

### `no_guidance`

- pretest is run
- learner state is still computed for logging
- no tutor plan is generated
- no intermediate practice is run
- no feedback is passed into posttest

### `generic_guidance`

- pretest is run
- a fixed, non-personalized hint is generated
- deterministic practice tasks are selected from reserve items, without learner-state adaptation
- practice responses are scored and recorded, but not included in final metrics
- a generic practice reminder is passed before posttest
- no adaptive plan is generated

### `adaptive_guidance`

- pretest is run
- learner state is computed
- tutor plan is generated
- per-item feedback is recorded
- next practice tasks are recommended
- recommended practice tasks are answered and scored before posttest
- practice feedback is summarized into the posttest prompt
- compact adaptive guidance is passed into posttest

The intermediate practice phase is deliberately non-scored for experiment metrics.
`round1_score`, `round2_score`, and `score_delta` still come only from fixed pretest
and fixed posttest bundles. Practice exists to make guidance operational in a
stateless LLM setup: the system must pass a compact summary of practice feedback
into the subsequent learner prompt, otherwise separate API calls would not share
learning context.

## 8. Experiment Artifacts

Each run directory currently contains:

- `interactions.jsonl`
- `states.jsonl`
- `plans.jsonl`
- `feedback.jsonl`
- `triage_training.jsonl`
- `efficiency.json`
- `metrics.csv`
- `cases.json`
- `report.md`

These files are sufficient to reconstruct:

- raw learner responses
- scoring outputs
- learner state evolution
- adaptive plan decisions
- final comparison tables

JSONL artifacts are flushed incrementally as records are produced. If an API run
fails before completion, completed interactions, states, plans, feedback, and
triage training rows remain available in the partially created run directory.

## 9. Current Design Decisions

### Single backend per run

One experiment run uses exactly one backend:

- all learner calls
- tutor calls
- judge calls

This keeps the execution path simple and reproducible.

### Practice recommendations are non-scored

Adaptive mode recommends extra tasks, but those tasks are not included in final score comparison.

This preserves fairness across:

- `no_guidance`
- `generic_guidance`
- `adaptive_guidance`

### Structured state and plan are explicit

Learner state and tutoring plan are first-class runtime objects, not hidden in prompts.

That means:

- the tutor plan can be inspected
- adaptive behavior is debuggable
- run artifacts are analyzable after execution

## 10. Known Weak Points

The current architecture is stable enough for a course prototype, but several weak points still affect experiment quality.

### Reading evaluation is still sensitive

Reading outcomes depend heavily on:

- answer phrasing
- evidence coverage thresholds
- judge-model behavior

### Pretest / posttest equivalence matters a lot

Even with fixed bundles, task difficulty mismatch can dominate the score delta.

### Learner realism still depends on model behavior

If the selected learner models are too strong or too instruction-following, they may not behave like constrained students even with a learner prompt.

### Adaptive signal is not yet isolated from all noise

The current architecture supports adaptive tutoring, but reported gains can still be overwhelmed by:

- task difficulty variance
- model instability
- scoring sensitivity

## 11. Recommended Extension Points

If this project is extended, the safest next modifications are:

- add more balanced tasks per bundle
- further tighten reading scoring
- split grammar and reading experiments if needed
- add richer case export for presentation
- support mixed backends per role if later needed
- add a dedicated experiment config for ablation studies

## 12. Summary

The current project architecture is centered on one orchestrator, one backend abstraction, explicit schemas, explicit learner state, and reproducible artifact output.

That makes it well-suited for:

- offline experiments
- course demos
- comparing guidance modes
- debugging adaptive tutoring behavior

It is not yet a product architecture, but it is a workable experiment architecture.
