# 분석 API — 카테고리 합계·비율·정렬, 0원 카테고리 제외, 전월 대비, 음수 지출(할인), 소비 조언(mock)

import pytest

from models import stats_model
from others import config
from services.advice import mock as advice_mock
from services.advice.errors import advice_timeout
from datetime import datetime, timezone

from tests.conftest import get_my_uid, get_test_db, post


def create(client, category, amount, occurred_on="2026-10-03", type="expense"):
    body = {"type": type, "amount": amount, "category": category, "title": "", "memo": "", "occurred_on": occurred_on}
    return post(client, "/transaction/create_transaction", body).json()["body"]


def stats(client, month="2026-10"):
    return client.get("/api/stats/get_category_stats", params={"month": month}).json()["body"]


def test_category_ratio_and_order(user_client):
    create(user_client, "식비", 412300)
    create(user_client, "생활", 338500)
    create(user_client, "교통", 368200)
    create(user_client, "급여", 2000000, type="income")  # 수입은 분석에서 뺀다

    body = stats(user_client)
    assert body["total_expense"] == 1119000
    assert [row["category"] for row in body["categories"]] == ["식비", "교통", "생활"]
    assert body["categories"][0] == {"category": "식비", "amount": 412300, "count": 1, "ratio": 36.8}
    assert body["categories"][2]["ratio"] == 30.3


def test_ratio_rounds_half_up(user_client):
    # 1/16 = 6.25% → 6.3, 15/16 = 93.75% → 93.8 (둘 다 0.05에서 올림)
    create(user_client, "식비", 1)
    create(user_client, "교통", 15)
    ratios = {row["category"]: row["ratio"] for row in stats(user_client)["categories"]}
    assert ratios == {"교통": 93.8, "식비": 6.3}


def test_discount_and_zero_category(user_client):
    create(user_client, "식비", 10000)
    item = create(user_client, "생활", 3000)["item"]
    # 생활 카테고리에 할인(음수) 내역을 직접 넣어 합계를 0원으로 만든다.
    now = datetime.now(timezone.utc)
    get_test_db().add_new_data(target="transactions", new_data={
        **item, "transaction_id": "discount-1", "amount": -3000, "uid": get_my_uid(user_client),
        "created_at": now, "updated_at": now})

    body = stats(user_client)
    assert body["total_expense"] == 10000
    assert [row["category"] for row in body["categories"]] == ["식비"]


def test_previous_month(user_client):
    create(user_client, "식비", 5000, occurred_on="2026-09-15")
    create(user_client, "식비", 7000, occurred_on="2026-10-15")
    body = stats(user_client)
    assert body["total_expense"] == 7000
    assert body["prev_month_expense"] == 5000


def test_january_compares_with_december(user_client):
    create(user_client, "식비", 4000, occurred_on="2025-12-31")
    assert stats(user_client, "2026-01")["prev_month_expense"] == 4000


def test_empty_month(user_client):
    body = stats(user_client, "2026-01")
    assert body["result"] is True
    assert body["total_expense"] == 0
    assert body["categories"] == []


def test_other_user_data_is_not_counted(user_client, other_client):
    create(user_client, "식비", 10000)
    assert stats(other_client)["total_expense"] == 0


def test_month_validation(user_client):
    assert stats(user_client, "2026/10")["fields"] == {"month": "월을 확인하세요"}


# ── 소비 조언 (POST /stats/analyze_spending) ──

@pytest.fixture
def fast_advice(monkeypatch):
    # 진행 표시용 지연을 없애고 mock 으로 고정한다.
    monkeypatch.setattr(advice_mock, "DELAY_SEC", 0)
    monkeypatch.setattr(config, "OCR_MODE", "mock")


def advice(client, month="2026-10"):
    return post(client, "/stats/analyze_spending", {"month": month}).json()["body"]


def test_advice_ok(user_client, fast_advice):
    create(user_client, "식비", 30000)
    create(user_client, "교통", 10000)
    body = advice(user_client)
    assert body["result"] is True
    assert body["month"] == "2026-10"
    assert body["summary"] == "이번 달 지출은 40,000원입니다. 식비 지출이 30,000원(75.0%)으로 가장 큽니다."
    assert len(body["advices"]) == 3
    assert (body["ai_provider"], body["ai_model"]) == ("mock", "")


def test_advice_sends_my_month_only(user_client, other_client, fast_advice, monkeypatch):
    # AI에 보내는 데이터: 내 내역만, 그 달만, 계정 정보·ID 없이
    create(user_client, "식비", 9000)
    create(user_client, "급여", 500000, type="income")
    create(user_client, "식비", 7000, occurred_on="2026-09-10")  # 지난달
    create(other_client, "쇼핑", 99000)                          # 다른 사용자
    sent = {}

    def fake_make_advice(spending):
        sent.update(spending)
        return {"summary": "요약", "advices": ["조언"]}

    monkeypatch.setattr(stats_model, "make_advice", fake_make_advice)
    assert advice(user_client)["advices"] == ["조언"]
    assert (sent["total_expense"], sent["total_income"], sent["prev_month_expense"]) == (9000, 500000, 7000)
    assert sent["categories"] == [{"category": "식비", "amount": 9000, "count": 1, "ratio": 100.0}]
    assert sorted(row["amount"] for row in sent["transactions"]) == [9000, 500000]
    assert set(sent["transactions"][0]) == {"date", "type", "category", "title", "merchant", "amount", "memo"}


def test_advice_no_data(user_client, fast_advice):
    body = advice(user_client, month="2026-08")
    assert (body["result"], body["error_code"], body["detail"]) == (False, "no_data", "분석할 내역이 없습니다")


def test_advice_bad_month(user_client, fast_advice):
    assert advice(user_client, month="2026-13")["error_code"] == "validation"


def test_advice_failure_is_passed_on(user_client, fast_advice, monkeypatch):
    create(user_client, "식비", 9000)

    def raise_timeout(spending):
        raise advice_timeout()

    monkeypatch.setattr(stats_model, "make_advice", raise_timeout)
    body = advice(user_client)
    assert (body["result"], body["error_code"], body["detail"]) == (False, "advice_timeout", "분석 시간이 초과되었습니다")


def test_advice_needs_login(client):
    assert post(client, "/stats/analyze_spending", {"month": "2026-10"}).status_code == 401
