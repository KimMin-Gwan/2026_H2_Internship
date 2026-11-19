# 영수증 분석 입구 — OCR_MODE 에 따라 mock, OpenAI, Claude 중 하나를 부른다. 돌려주는 값은 모델 출력 모양(schema.py)의 dict 다.
#
# 두 모델 모두 HTTP 요청 한 번이고, 프롬프트(prompt.py)와 JSON 스키마(schema.py)는 같은 것을 쓴다.
# 다른 것은 주소, 인증 헤더, 요청·응답의 모양뿐이다 (05 문서 1절).
#   OpenAI: Responses API. 이미지는 data URL, 스키마는 text.format
#   Claude: Messages API. 이미지는 base64 블록, 스키마는 output_config.format

import base64
import json
import time

import httpx

from others import config
from services.ocr import mock
from services.ocr.errors import ocr_failed, ocr_timeout
from services.ocr.prompt import SYSTEM_PROMPT, USER_PROMPT
from services.ocr.schema import RECEIPT_SCHEMA

OPENAI_URL = "https://api.openai.com/v1/responses"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_API_VERSION = "2023-06-01"
# 답(JSON)의 최대 길이. 품목이 많은 영수증도 담기는 크기
CLAUDE_MAX_TOKENS = 4096
# 답이 깨졌을 때 다시 묻는 횟수까지 합친 최대 시도 횟수 (처음 1번 + 재시도 1번)
MAX_TRIES = 2


# 지금 설정으로 분석에 쓰는 AI. 화면에 보여 주고 영수증 문서에 남긴다. mock 이면 모델 이름은 빈 문자열
def get_ocr_engine() -> dict:
    if config.OCR_MODE == "mock":
        return {"ocr_provider": "mock", "ocr_model": ""}
    if config.OCR_MODE == "claude":
        return {"ocr_provider": "claude", "ocr_model": config.ANTHROPIC_MODEL}
    return {"ocr_provider": "openai", "ocr_model": config.OPENAI_MODEL}


def analyze_receipt(image: bytes) -> dict:
    if config.OCR_MODE == "mock":
        return mock.analyze(config.OCR_MOCK_SCENARIO)
    if config.OCR_MODE == "claude":
        return _analyze_with_model(image=image, api_key=config.ANTHROPIC_API_KEY, call_model=_call_claude)
    return _analyze_with_model(image=image, api_key=config.OPENAI_API_KEY, call_model=_call_openai)


# 전체 시도가 OCR_TIMEOUT_SEC 안에 끝나야 한다. 답이 JSON 이 아니거나 모양이 틀리면 한 번만 다시 묻는다.
# call_model 은 모델을 한 번 부르고 답(문자열)을 돌려주는 함수다 (_call_openai, _call_claude).
def _analyze_with_model(image: bytes, api_key: str, call_model) -> dict:
    if not api_key:
        raise ocr_failed()

    deadline = time.monotonic() + config.OCR_TIMEOUT_SEC
    for _ in range(MAX_TRIES):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ocr_timeout()
        result = _parse_json(call_model(image=image, timeout=remaining))
        if result is not None:
            return result
    raise ocr_failed()


# ── OpenAI ──

def _request_body(image: bytes) -> dict:
    image_url = "data:image/jpeg;base64," + base64.b64encode(image).decode("ascii")
    return {
        "model": config.OPENAI_MODEL,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "input_text", "text": USER_PROMPT},
                {"type": "input_image", "image_url": image_url},
            ]},
        ],
        "text": {"format": {"type": "json_schema", "name": "receipt", "schema": RECEIPT_SCHEMA, "strict": True}},
    }


# 모델의 답(문자열)을 돌려준다.
def _call_openai(image: bytes, timeout: float) -> str:
    data = _post_json(url=OPENAI_URL, body=_request_body(image), timeout=timeout,
                      headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"})
    return _output_text(data)


# 응답의 output 중 message 의 output_text 를 찾는다. 모델이 거절(refusal)했으면 ocr_failed
def _output_text(data: dict) -> str:
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for part in output.get("content", []):
            if part.get("type") == "output_text":
                return part.get("text", "")
    raise ocr_failed()


# ── Claude ──

def _claude_request_body(image: bytes) -> dict:
    return {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(image).decode("ascii")}},
                {"type": "text", "text": USER_PROMPT},
            ]},
        ],
        "output_config": {"format": {"type": "json_schema", "schema": RECEIPT_SCHEMA}},
    }


# 모델의 답(문자열)을 돌려준다.
def _call_claude(image: bytes, timeout: float) -> str:
    data = _post_json(url=CLAUDE_URL, body=_claude_request_body(image), timeout=timeout,
                      headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": CLAUDE_API_VERSION})
    return _claude_output_text(data)


# 응답의 content 중 text 블록을 찾는다. 모델이 거절했거나(refusal) 답이 중간에 잘렸으면(max_tokens) ocr_failed
def _claude_output_text(data: dict) -> str:
    if data.get("stop_reason") in ("refusal", "max_tokens"):
        raise ocr_failed()
    for block in data.get("content", []):
        if block.get("type") == "text":
            return block.get("text", "")
    raise ocr_failed()


# ── 공통 ──

# HTTP 요청을 한 번 보내고 응답(JSON)을 dict 로 돌려준다. 시간 초과는 ocr_timeout, 그 밖의 실패는 ocr_failed
def _post_json(url: str, body: dict, headers: dict, timeout: float) -> dict:
    try:
        res = httpx.post(url, json=body, timeout=timeout, headers=headers)
    except httpx.TimeoutException:
        raise ocr_timeout()
    except httpx.HTTPError:
        raise ocr_failed()
    if res.status_code != 200:
        raise ocr_failed()
    try:
        data = res.json()
    except ValueError:
        raise ocr_failed()
    if not isinstance(data, dict):
        raise ocr_failed()
    return data


# JSON 이고 모양이 맞으면 dict, 아니면 None (다시 묻는다)
def _parse_json(text: str):
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        return None
    return result
