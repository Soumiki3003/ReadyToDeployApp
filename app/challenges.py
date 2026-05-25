UNLOCK_SEQUENCE = ['pre_study'] + [f'ctf_{i:02d}' for i in range(18)] + ['post_study']

CHALLENGE_LABELS = {
    'pre_study': 'Pre-Study',
    **{f'ctf_{i:02d}': f'CTF-{i:02d}' for i in range(18)},
    'post_study': 'Post-Study',
}

POST_STUDY_STAGE = len(UNLOCK_SEQUENCE) - 1  # index 19


def get_current_stage(completed_survey_ids: list[str]) -> int:
    """Number of surveys completed in sequence order = the stage the student is now on."""
    stage = 0
    for survey_id in UNLOCK_SEQUENCE:
        if survey_id in completed_survey_ids:
            stage += 1
        else:
            break
    return stage


def survey_for_stage(stage: int) -> str | None:
    """The survey that must be submitted to advance past this stage."""
    if 0 <= stage < len(UNLOCK_SEQUENCE):
        return UNLOCK_SEQUENCE[stage]
    return None


def build_breadcrumb(course_id: str, current_stage: int, viewed_stage: int) -> list[dict]:
    items = []
    for i, survey_id in enumerate(UNLOCK_SEQUENCE):
        if i == 0:
            url = f'/course/{course_id}/pre-study'
        elif i == POST_STUDY_STAGE:
            url = f'/course/{course_id}/post-study'
        else:
            url = f'/course/{course_id}/challenge/{i}'
        items.append({
            'label': CHALLENGE_LABELS[survey_id],
            'stage': i,
            'url': url,
            'unlocked': i <= current_stage,
            'completed': i < current_stage,
            'active': i == viewed_stage,
        })
    return items
