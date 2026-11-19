# 소비 조언 출력 스키마(JSON Schema) — 모델이 반드시 이 모양으로만 답하게 한다 (05 문서 9절).

ADVICE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "advices"],
    "properties": {
        "summary": {"type": "string", "description": "이번 달 소비 패턴 요약, 2~3문장"},
        "advices": {
            "type": "array",
            "description": "실천할 수 있는 조언 3개, 각 1~2문장",
            "items": {"type": "string"},
        },
    },
}
