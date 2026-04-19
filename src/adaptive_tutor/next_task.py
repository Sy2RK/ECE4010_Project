from __future__ import annotations

from adaptive_tutor.schemas import Task, TutoringPlan


def recommend_tasks(
    tasks: dict[str, Task],
    tutoring_plan: TutoringPlan,
    exclude_task_ids: set[str],
) -> list[Task]:
    focus_terms = {tutoring_plan.focus_skill, *tutoring_plan.focus_subskills}
    candidates: list[tuple[int, int, str, Task]] = []
    for task in tasks.values():
        if task.task_id in exclude_task_ids:
            continue
        if task.task_type != tutoring_plan.next_task_type:
            continue
        skill_match = len(set(task.skill_tags) & focus_terms)
        difficulty_gap = abs(task.difficulty - tutoring_plan.recommended_difficulty)
        candidates.append((skill_match, -difficulty_gap, task.task_id, task))
    candidates.sort(reverse=True)
    return [task for *_rest, task in candidates[: tutoring_plan.next_batch_size]]
