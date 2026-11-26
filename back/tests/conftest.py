# 테스트 설정 — app을 불러오기 전에 환경 변수를 정해야 한다.
# DB는 .env 의 DB_TYPE 을 따른다 (mongo | sqlite). 다른 쪽으로 돌리려면 PowerShell 에서: $env:DB_TYPE="sqlite"; pytest
# mongo 이고 Atlas 주소가 없으면 먼저 docker compose up -d mongo 로 DB를 띄운다. sqlite 는 준비할 것이 없다.

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# DB 주소는 .env 의 MONGODB_URI(Atlas)를 쓰되, DB 이름은 별도(yeongsugori_test)로 한다. 실제 데이터와 섞이지 않는다.
# 주소가 비어 있거나 docker 안에서만 통하는 주소(mongo:27017)면 이 PC의 mongo 를 쓴다.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
if not os.getenv("MONGODB_URI") or "//mongo:" in os.getenv("MONGODB_URI"):
    os.environ["MONGODB_URI"] = "mongodb://localhost:27017"

# 나머지는 .env 와 상관없이 정한다: 테스트 DB, 임시 폴더(영수증 이미지), mock 분석
# (config.py 는 .env 를 읽지만 이미 있는 환경 변수는 덮어쓰지 않는다)
os.environ["MONGODB_DB"] = "yeongsugori_test"
# sqlite 일 때는 임시 폴더의 파일을 쓴다 (실제 DB 파일과 섞이지 않는다)
os.environ["SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(prefix="yeongsugori_db_"), "test.db")
os.environ["OCR_MODE"] = "mock"
os.environ["MAX_UPLOAD_MB"] = "10"
os.environ["SCAN_LIMIT_PER_HOUR"] = "20"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="yeongsugori_uploads_")
# 테스트에서만 쓰는 서명 키
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-for-pytest-0123456789"

import pytest  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from data_domains.yeongsugori_data_domain import Receipt  # noqa: E402
from main import app  # noqa: E402
from models import make_database  # noqa: E402

PASSWORD = "demo1234a"


# 앱과 같은 DB 객체 (MongoDB 또는 SQLite). 테스트가 DB를 직접 들여다보거나 고칠 때 쓴다.
def get_test_db():
    return make_database()


# 영수증 문서를 DB에 직접 넣는다 (이미지는 없다). 내역에 영수증 ID를 붙이는 테스트용
def add_test_receipt(uid: str, receipt_id: str = "receipt-1") -> None:
    receipt = Receipt(receipt_id=receipt_id, uid=uid, image_key=f"receipts/{uid}/{receipt_id}.jpg", status="confirmed",
                      parsed_json="{}", confidence="high", ocr_provider="mock", created_at=datetime.now(timezone.utc))
    get_test_db().add_new_data(target="receipts", new_data=receipt.get_dict_form_data())


def get_my_uid(client) -> str:
    return client.get("/api/auth/get_me").json()["body"]["user"]["uid"]


def post(client, path, body):
    return client.post("/api" + path, json={"header": {}, "body": body})


def signup(client, email="demo@yeongsugori.test", nickname="기록하는사람", password=PASSWORD):
    return post(client, "/auth/signup", {"email": email, "nickname": nickname, "password": password})


# 테스트마다 데이터를 비우고, 쿠키가 없는 새 클라이언트로 시작한다.
@pytest.fixture
def client():
    database = get_test_db()
    for name in ["transactions", "receipts", "users"]:  # 다른 것을 가리키는 쪽부터 지운다
        database.delete_all_data(target=name)
    return TestClient(app)


# 가입(=로그인)까지 마친 클라이언트
@pytest.fixture
def user_client(client):
    signup(client)
    return client


# 다른 사용자로 로그인한 클라이언트 (내 데이터가 보이지 않는지 확인용)
@pytest.fixture
def other_client(client):
    other = TestClient(app)
    signup(other, email="other@yeongsugori.test", nickname="다른사람")
    return other
