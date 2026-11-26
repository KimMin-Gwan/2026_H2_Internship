# DB 연결 확인 — .env 의 DB_TYPE 에 따라 MongoDB 또는 SQLite

from models import make_database


def test_db_ping():
    database = make_database()
    assert database.ping()
