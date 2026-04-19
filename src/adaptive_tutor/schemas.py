from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TaskType = Literal["grammar_correction", "reading_qa"]
GuidanceMode = Literal["no_guidance", "generic_guidance", "adaptive_guidance"]
InteractionPhase = Literal["pretest", "posttest"]
FeedbackStyle = Literal[
    "concise_correction",
    "correction_brief_explanation",
    "step_by_step_hint",
    "generic_guidance",
]
HintLevel = Literal["low", "medium", "high"]
TriageMode = Literal["shadow", "enforce"]


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_type: TaskType
    difficulty: int = Field(ge=1, le=3)
    skill_tags: list[str]
    prompt: str | None = None
    input_text: str | None = None
    passage: str | None = None
    question: str | None = None
    reference_answer: str

    @model_validator(mode="after")
    def validate_task_shape(self) -> "Task":
        if self.task_type == "grammar_correction":
            if not self.prompt or not self.input_text:
                raise ValueError("grammar_correction requires prompt and input_text")
            if self.passage or self.question:
                raise ValueError("grammar_correction must not define passage or question")
        if self.task_type == "reading_qa":
            if not self.passage or not self.question:
                raise ValueError("reading_qa requires passage and question")
            if self.prompt or self.input_text:
                raise ValueError("reading_qa must not define prompt or input_text")
        return self


class LearnerProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    weak_skills: list[str]
    mid_skills: list[str]
    strong_skills: list[str]
    typical_errors: list[str]
    answer_style: str
    model_id_override: str | None = None


class BundleAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pretest_bundle: str
    posttest_bundle: str


class BundleCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_definitions: dict[str, list[str]]
    assignments: dict[str, dict[TaskType, BundleAssignment]]

    @model_validator(mode="after")
    def validate_bundle_references(self) -> "BundleCatalog":
        defined = set(self.bundle_definitions)
        for learner_id, task_map in self.assignments.items():
            for task_type, assignment in task_map.items():
                if assignment.pretest_bundle not in defined:
                    raise ValueError(
                        f"{learner_id}/{task_type} references missing bundle {assignment.pretest_bundle}"
                    )
                if assignment.posttest_bundle not in defined:
                    raise ValueError(
                        f"{learner_id}/{task_type} references missing bundle {assignment.posttest_bundle}"
                    )
                pre = set(self.bundle_definitions[assignment.pretest_bundle])
                post = set(self.bundle_definitions[assignment.posttest_bundle])
                if pre & post:
                    raise ValueError(
                        f"{learner_id}/{task_type} pretest and posttest bundles overlap"
                    )
        return self


class BackendConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["mock", "openai_compatible"]
    base_url: str | None = None
    api_key: str | None = None
    timeout_seconds: float = Field(default=30.0, gt=0)
    retry_attempts: int = Field(default=3, ge=1)
    retry_backoff_seconds: float = Field(default=1.0, ge=0)


class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shared_learner_model: str = Field(min_length=1)
    tutor_model: str = Field(min_length=1)
    judge_model: str = Field(min_length=1)
    learner_model_overrides: dict[str, str] = Field(default_factory=dict)

    @field_validator("shared_learner_model", "tutor_model", "judge_model")
    @classmethod
    def validate_required_model_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("model name must not be empty")
        return stripped

    @field_validator("learner_model_overrides")
    @classmethod
    def normalize_learner_model_overrides(cls, value: dict[str, str]) -> dict[str, str]:
        return {key: item.strip() for key, item in value.items()}


class ReadingJudgeTriageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    mode: TriageMode = "shadow"
    model_path: str = "models/reading_judge_triage.pt"
    confidence_threshold: float = Field(default=0.90, ge=0, le=1)
    collect_training_data: bool = True


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: BackendConfig
    models: ModelsConfig
    learners_path: str
    tasks_path: str
    bundles_path: str
    output_root: str = "outputs"
    run_name: str | None = None
    seed: int = 42
    modes: list[GuidanceMode] = Field(
        default_factory=lambda: [
            "no_guidance",
            "generic_guidance",
            "adaptive_guidance",
        ]
    )
    judge_gray_zone: tuple[float, float] = (0.25, 0.75)
    reading_judge_triage: ReadingJudgeTriageConfig = Field(
        default_factory=ReadingJudgeTriageConfig
    )

    @model_validator(mode="after")
    def validate_gray_zone(self) -> "AppConfig":
        low, high = self.judge_gray_zone
        if not 0 <= low <= high <= 1:
            raise ValueError("judge_gray_zone must satisfy 0 <= low <= high <= 1")
        return self


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, le=1)
    error_tags: list[str] = Field(default_factory=list)
    evaluator_note: str | None = None
    used_judge: bool = False
    scoring_source: str | None = None
    rule_score: float | None = None
    used_triage: bool = False
    triage_candidate: bool = False
    triage_would_skip: bool = False
    triage_confidence: float | None = None
    triage_prediction: float | None = None
    triage_features: list[list[float]] | None = None


class StateVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grammar: float = Field(ge=0, le=1)
    vocabulary: float = Field(ge=0, le=1)
    reading: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class RecentErrorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_errors: list[str]
    weakest_skill: str


class LearnerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    state_vector: StateVector
    recent_error_summary: RecentErrorSummary


class TutoringPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus_skill: str
    focus_subskills: list[str]
    recommended_difficulty: int = Field(ge=1, le=3)
    feedback_style: FeedbackStyle
    hint_level: HintLevel
    next_task_type: TaskType
    next_batch_size: int = Field(ge=1, le=5)
    adaptation_rationale: str

    @model_validator(mode="after")
    def validate_plan(self) -> "TutoringPlan":
        if self.feedback_style == "generic_guidance":
            raise ValueError("generic_guidance is not a valid adaptive feedback style")
        if not self.focus_subskills:
            raise ValueError("focus_subskills must not be empty")
        return self


class JudgeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: Literal[0.0, 0.5, 1.0]
    note: str


class InteractionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_id: str
    learner_id: str
    task_id: str
    task_type: TaskType
    difficulty: int = Field(ge=1, le=3)
    response_text: str
    score: float = Field(ge=0, le=1)
    error_tags: list[str]
    guidance_mode: GuidanceMode
    round_index: int = Field(ge=1)
    phase: InteractionPhase
    evaluator_note: str | None = None
    scoring_source: str | None = None
    rule_score: float | None = None
    used_judge: bool = False
    used_triage: bool = False
    triage_candidate: bool = False
    triage_would_skip: bool = False
    triage_confidence: float | None = None
    triage_prediction: float | None = None


class StateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    task_type: TaskType
    guidance_mode: GuidanceMode
    round_index: int = Field(ge=1)
    learner_state: LearnerState


class PlanRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    task_type: TaskType
    guidance_mode: GuidanceMode
    round_index: int = Field(ge=1)
    tutoring_plan: TutoringPlan
    recommended_task_ids: list[str] = Field(default_factory=list)


class FeedbackRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    task_id: str
    task_type: TaskType
    guidance_mode: GuidanceMode
    round_index: int = Field(ge=1)
    feedback_style: FeedbackStyle
    feedback_text: str
    next_task_recommendation: list[str] = Field(default_factory=list)
    focus_skill: str | None = None


class ExperimentMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    mode: GuidanceMode
    task_type: TaskType
    round1_score: float = Field(ge=0, le=1)
    round2_score: float = Field(ge=0, le=1)
    score_delta: float


class RunArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interactions: list[InteractionRecord]
    states: list[StateRecord]
    plans: list[PlanRecord]
    feedback: list[FeedbackRecord]
    metrics: list[ExperimentMetric]
    cases: list[dict[str, Any]]
