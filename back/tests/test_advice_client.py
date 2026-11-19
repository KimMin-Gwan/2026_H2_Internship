# 소비 조언 호출(services/advice/client.py) — 실제 네트워크 대신 가짜 응답으로 확인한다. 실제 호출은 맨 아래 live 테스트

import json
import os

import httpx
import pytest

from others import config
from services.advice import client, mock
from services.advice.errors import AdviceError
from services.ocr import client as ocr_client

SPENDING = {
    "month": "2026-10", "total_expense": 40000, "total_income": 0, "prev_month_expense": 0,
    "categories": [{"category": "식비", "amount": 30000, "count": 2, "ratio": 75.0},
                   {"category": "교통", "amount": 10000, "count": 1, "ratio": 25.0}],
    "transactions": [
        {"date": "2026-10-03", "type": "expense", "category": "식비", "title": "김치찌개", "merchant": None, "amount": 9000, "memo": ""},
        {"date": "2026-10-02", "type": "expense", "category": "식비", "title": "마트", "merchant": "한빛마트", "amount": 21000, "memo": ""},
        {"date": "2026-10-01", "type": "expense", "category": "교통", "title": "교통카드 충전", "merchant": None, "amount": 10000, "memo": ""},
    ],
}
GOOD = {"summary": "식비가 가장 큽니다.", "advices": ["조언 1", "조언 2", "조언 3"]}


def claude_response(text: str, status: int = 200, stop_reason: str = "end_turn") -> httpx.Response:
    return httpx.Response(status, json={"stop_reason": stop_reason, "content": [{"type": "text", "text": text}]})


def openai_response(text: str) -> httpx.Response:
    return httpx.Response(200, json={"output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]})


@pytest.fixture
def claude_mode(monkeypatch):
    monkeypatch.setattr(config, "OCR_MODE", "claude")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(config, "ANTHROPIC_MODEL", "test-model")
    monkeypatch.setattr(config, "OCR_TIMEOUT_SEC", 30)


def fake_post(monkeypatch, *responses):
    # 부를 때마다 responses 를 하나씩 돌려준다. 예외면 그 예외를 던진다.
    calls = []

    def post(url, json, timeout, headers):
        calls.append({"url": url, "json": json, "timeout": timeout, "headers": headers})
        result = responses[len(calls) - 1]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(ocr_client.httpx, "post", post)
    return calls


def test_mock_uses_numbers(monkeypatch):
    monkeypatch.setattr(config, "OCR_MODE", "mock")
    monkeypatch.setattr(mock, "DELAY_SEC", 0)
    result = client.make_advice(SPENDING)
    assert result["summary"] == "이번 달 지출은 40,000원입니다. 식비 지출이 30,000원(75.0%)으로 가장 큽니다."
    assert len(result["advices"]) == 3


def test_claude_request_shape(claude_mode, monkeypatch):
    calls = fake_post(monkeypatch, claude_response(json.dumps(GOOD, ensure_ascii=False)))
    assert client.make_advice(SPENDING) == GOOD

    request = calls[0]
    assert request["url"] == "https://api.anthropic.com/v1/messages"
    assert request["headers"]["x-api-key"] == "test-key"
    body = request["json"]
    assert body["model"] == "test-model"
    assert body["system"] == client.SYSTEM_PROMPT
    assert body["output_config"]["format"]["schema"] == client.ADVICE_SCHEMA
    # 소비 데이터가 JSON 그대로 붙어 간다 (한글은 그대로)
    message = body["messages"][0]["content"]
    assert message.startswith("다음은 2026-10 소비 데이터입니다.\n")
    assert json.loads(message.split("\n", 1)[1]) == SPENDING
    assert "김치찌개" in message


def test_openai_request_shape(monkeypatch):
    monkeypatch.setattr(config, "OCR_MODE", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(config, "OPENAI_MODEL", "test-model")
    calls = fake_post(monkeypatch, openai_response(json.dumps(GOOD, ensure_ascii=False)))
    assert client.make_advice(SPENDING) == GOOD
    body = calls[0]["json"]
    assert calls[0]["url"] == "https://api.openai.com/v1/responses"
    assert body["text"]["format"]["schema"] == client.ADVICE_SCHEMA
    assert body["input"][1]["content"].startswith("다음은 2026-10 소비 데이터입니다.")


def test_answer_is_cleaned(claude_mode, monkeypatch):
    # 빈 조언·문자열이 아닌 값은 버리고, 줄바꿈은 공백으로, 조언은 5개까지
    answer = {"summary": " 요약\n입니다. ", "advices": ["하나", "", 3, "둘\n셋", "넷", "다섯", "여섯", "일곱"]}
    fake_post(monkeypatch, claude_response(json.dumps(answer, ensure_ascii=False)))
    assert client.make_advice(SPENDING) == {"summary": "요약 입니다.", "advices": ["하나", "둘 셋", "넷", "다섯", "여섯"]}


@pytest.mark.parametrize("response, code", [
    (httpx.ReadTimeout("slow"), "advice_timeout"),
    (httpx.ConnectError("no network"), "advice_failed"),
    (claude_response("", status=500), "advice_failed"),
    (claude_response("", stop_reason="refusal"), "advice_failed"),
    (claude_response("not json {"), "advice_failed"),
    (claude_response('{"summary": "", "advices": ["조언"]}'), "advice_failed"),
    (claude_response('{"summary": "요약", "advices": []}'), "advice_failed"),
    (claude_response('["요약"]'), "advice_failed"),
])
def test_failures(claude_mode, monkeypatch, response, code):
    calls = fake_post(monkeypatch, response)
    with pytest.raises(AdviceError) as error:
        client.make_advice(SPENDING)
    assert error.value.code == code
    assert len(calls) == 1  # 다시 묻지 않는다


def test_no_key_is_advice_failed(claude_mode, monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    calls = fake_post(monkeypatch)
    with pytest.raises(AdviceError) as error:
        client.make_advice(SPENDING)
    assert error.value.code == "advice_failed"
    assert calls == []


# ── 실제 Claude 호출 (비용 발생). ANTHROPIC_API_KEY 가 있을 때 pytest -m live 로만 돈다 ──

@pytest.mark.live
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY 가 없다")
def test_live_claude_advice(monkeypatch):
    monkeypatch.setattr(config, "OCR_MODE", "claude")
    result = client.make_advice(SPENDING)
    assert result["summary"]
    assert 1 <= len(result["advices"]) <= 5
