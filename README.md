# Adaptive English AI Tutor

Lightweight offline prototype for adaptive tutoring experiments with learner agents,
learner state modeling, structured tutoring plans, and report generation.

## Quick start

```powershell
pip install -e .[dev]
```

If you want to train or run the local PyTorch GRU reading judge triage model:

```powershell
pip install -e .[dev,ml]
```

### API mode (default)

1. Copy `.env.example` to `.env`
2. Fill `DASHSCOPE_API_KEY`, `SHARED_LEARNER_MODEL`, `TUTOR_MODEL`, and `JUDGE_MODEL`
3. Optional: fill `LEARNER_A_MODEL`, `LEARNER_B_MODEL`, `LEARNER_C_MODEL` if you want each learner to use a different model
4. Run:

```powershell
python -m adaptive_tutor run-experiment --config data/config.sample.yaml
```

`data/config.sample.yaml` now defaults to the DashScope OpenAI-compatible endpoint:
`https://dashscope.aliyuncs.com/compatible-mode/v1`

Learner model resolution order is:
1. `models.learner_model_overrides.<learner_id>`
2. `learners.json` -> `model_id_override`
3. `models.shared_learner_model`

### Mock mode

If you want an offline demo without API credentials:

```powershell
python -m adaptive_tutor run-experiment --config data/config.mock.yaml
```

Both modes create a run directory under `outputs/` with JSONL artifacts, CSV metrics,
and a Markdown report.

The API backend retries transient provider failures with exponential backoff. Run
artifacts are incrementally flushed to JSONL files during execution, so completed
interactions are preserved even if a later API call fails.

### Reading judge triage

The project can optionally use a local PyTorch GRU triage model before calling the
LLM judge for Reading QA gray-zone answers. This is disabled by default.

1. Run shadow mode to collect judge-labeled training rows:

```powershell
python -m adaptive_tutor run-experiment --config data/config.triage.yaml
```

2. Train the local triage model:

```powershell
python -m adaptive_tutor train-reading-triage --runs outputs/sample_api_triage_run --model-path models/reading_judge_triage.pt
```

3. Change `reading_judge_triage.mode` to `enforce` after shadow validation is acceptable.

Triage artifacts:
- `triage_training.jsonl`: judge-labeled GRU training rows
- `efficiency.json`: judge calls, triage skips, and estimated saved API calls
- `report.md`: includes an efficiency section

`outputs/` contains illustrative sample runs, not regression fixtures. Behavioral
regression checks live under `tests/`.

Do not commit `.env`, `outputs/`, caches, or local model checkpoints. The repository
`.gitignore` excludes these generated or secret-bearing files.

## Architecture

Detailed architecture notes are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
