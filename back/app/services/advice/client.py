# 소비 조언 입구 — OCR_MODE 에 따라 mock, OpenAI, Claude 중 하나에 한 달 소비 데이터를 보내고 조언을 받는다.
# 돌려주는 값은 {"summary": 문자열, "advices": [문자열, ...]} 이다 (schema.py).
#
# 영수증 분석(services/ocr/client.py)과 같은 키·모델·시간 제한을 쓰고, HTTP 호출 함수도 그쪽 것을 쓴다.
# 다른 점은 이미지 대신 글(소비 데이터 JSON)을 보낸다는 것뿐이다.

import json

from others import config
from services.advice import mock
from services.advice.errors import AdviceError, advice_failed, advice_timeout
from services.advice.prompt import SYSTEM_PROMPT, make_user_prompt
from services.advice.schema import ADVICE_SCHEMA
from services.ocr.client import (CLAUDE_API_VERSION, CLAUDE_URL, OPENAI_URL, claude_output_text, openai_output_text,
                                 post_json)
from services.ocr.errors import OcrError

# 답(JSON)의 최대 길이. 요약 2~3문장 + 조언 3개가 넉넉히 담기는 크기
CLAUDE_MAX_TOKENS = 1024
MAX_ADVICES = 5
MAX_TEXT = 300


def make_advice(spending: dict) -> dict:
    if config.OCR_MODE == "mock":
        return mock.advise(spending)

    user_prompt = make_user_prompt(spending)
    try:
        if config.OCR_MODE == "claude":
            text = _ask_claude(user_prompt)
        else:
            text = _ask_openai(user_prompt)
    except OcrError as error:
        # HTTP 호출 함수가 영수증 분석용 오류를 던지므로 조언용 오류로 바꾼다.
        raise advice_timeout() if error.code == "ocr_timeout" else advice_failed()
    return _clean(text)


def _ask_claude(user_prompt: str) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise advice_failed()
    body = {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
        "output_config": {"format": {"type": "json_schema", "schema": ADVICE_SCHEMA}},
    }
    data = post_json(url=CLAUDE_URL, body=body, timeout=config.OCR_TIMEOUT_SEC,
                     headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": CLAUDE_API_VERSION})
    return claude_output_text(data)


def _ask_openai(user_prompt: str) -> str:
    if not config.OPENAI_API_KEY:
        raise advice_failed()
    body = {
        "model": config.OPENAI_MODEL,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "text": {"format": {"type": "json_schema", "name": "advice", "schema": ADVICE_SCHEMA, "strict": True}},
    }
    data = post_json(url=OPENAI_URL, body=body, timeout=config.OCR_TIMEOUT_SEC,
                     headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"})
    return openai_output_text(data)


# 모델의 답(문자열)을 확인하고 정리한다. JSON 이 아니거나 모양이 틀리면 advice_failed
def _clean(text: str) -> dict:
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        raise advice_failed()
    if not isinstance(result, dict):
        raise advice_failed()

    summary = result.get("summary")
    advices = result.get("advices")
    if not isinstance(summary, str) or not summary.strip() or not isinstance(advices, list):
        raise advice_failed()
    advices = [" ".join(advice.split())[:MAX_TEXT] for advice in advices if isinstance(advice, str) and advice.strip()]
    if not advices:
        raise advice_failed()
    return {"summary": " ".join(summary.split())[:MAX_TEXT * 2], "advices": advices[:MAX_ADVICES]}
