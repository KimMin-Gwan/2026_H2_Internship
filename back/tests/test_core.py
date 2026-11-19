# 서버 상태 확인, 카테고리 목록 API — 먼저 docker compose up -d mongo 로 DB를 띄운다.

from fastapi.testclient import TestClient

from main import app
from models import HealthModel, Mongo_Database
from others import config
from utils import Head_Parser

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"header": {}, "body": {"result": True, "detail": "", "status": "ok"}}


def test_health_db_down():
    # 아무것도 없는 포트로 연결해 DB가 꺼진 상황을 만든다.
    model = HealthModel(database=Mongo_Database(uri="mongodb://localhost:1", db_name="yeongsugori_test"))
    model.check_health()
    body = model.get_response_form_data(Head_Parser())["body"]
    assert body == {"result": False, "detail": "DB에 연결하지 못했습니다", "error_code": "server", "status": "db_error"}


def test_get_categories():
    body = client.get("/api/meta/get_categories").json()["body"]
    assert body["result"] is True
    assert body["expense"][0] == "식비"
    assert body["income"] == ["급여", "용돈", "기타수입"]


def test_get_ocr_engine(monkeypatch):
    monkeypatch.setattr(config, "OCR_MODE", "mock")
    body = client.get("/api/meta/get_ocr_engine").json()["body"]
    assert body == {"result": True, "detail": "", "ocr_provider": "mock", "ocr_model": ""}

    monkeypatch.setattr(config, "OCR_MODE", "claude")
    monkeypatch.setattr(config, "ANTHROPIC_MODEL", "test-model")
    body = client.get("/api/meta/get_ocr_engine").json()["body"]
    assert (body["ocr_provider"], body["ocr_model"]) == ("claude", "test-model")
