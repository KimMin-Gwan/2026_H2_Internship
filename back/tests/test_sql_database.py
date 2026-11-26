# SQLite DB 클래스(Sql_Database) — MongoDB 없이 돈다. 임시 파일에 테이블을 만들고 메서드를 하나씩 확인한다.

from datetime import datetime, timedelta, timezone

import pytest

from models.database.errors import DatabaseError, DuplicateKeyError
from models.database.sql_database_model import Sql_Database

NOW = datetime(2026, 11, 2, 5, 21, 0, tzinfo=timezone.utc)


def user(uid="u1", email="demo@yeongsugori.test"):
    return {"uid": uid, "email": email, "password_hash": "hash", "nickname": "기록하는사람", "created_at": NOW}


def transaction(transaction_id, amount, category="식비", type="expense", occurred_on="2026-11-02", uid="u1", receipt_id=None):
    return {"transaction_id": transaction_id, "uid": uid, "type": type, "amount": amount, "category": category,
            "title": "점심", "merchant": None, "memo": "", "occurred_on": occurred_on, "receipt_id": receipt_id,
            "created_at": NOW, "updated_at": NOW}


def receipt(receipt_id="r1", uid="u1", created_at=NOW):
    return {"receipt_id": receipt_id, "uid": uid, "image_key": f"receipts/{uid}/{receipt_id}.jpg", "status": "analyzed",
            "merchant": "한빛마트", "purchased_on": "2026-11-02", "total_amount": 14200, "parsed_json": "{}",
            "confidence": "high", "ocr_provider": "mock", "ocr_model": "", "created_at": created_at}


@pytest.fixture
def database(tmp_path):
    database = Sql_Database(path=str(tmp_path / "sub" / "test.db"))  # 없는 폴더는 만든다
    database.make_indexes()
    database.make_indexes()  # 두 번 불러도 된다
    database.add_new_data(target="users", new_data=user())
    return database


def test_ping_and_categories(database):
    assert database.ping()
    names = [row["name"] for row in database.get_list_with_query(target="categories", query={"type": "income"}, sort=[("sort_order", 1)])]
    assert names == ["급여", "용돈", "기타수입"]
    assert database.count_with_query(target="categories", query={}) == 12


def test_get_one(database):
    found = database.get_data_with_key(target="users", key="email", key_data="demo@yeongsugori.test")
    assert found["uid"] == "u1"
    assert found["created_at"] == NOW.replace(tzinfo=None)  # 시각은 datetime 으로 돌아온다 (UTC, 시간대 표시 없음)
    assert database.get_data_with_key(target="users", key="uid", key_data="none") is None
    assert database.get_data_with_query(target="users", query={"uid": "u1", "nickname": "다른사람"}) is None


def test_duplicate_email(database):
    with pytest.raises(DuplicateKeyError):
        database.add_new_data(target="users", new_data=user(uid="u2"))


def test_list_range_and_sort(database):
    database.add_new_data(target="transactions", new_data=transaction("t1", 9000, occurred_on="2026-10-31"))
    database.add_new_data(target="transactions", new_data=transaction("t2", 4500, occurred_on="2026-11-01"))
    database.add_new_data(target="transactions", new_data=transaction("t3", 1500, occurred_on="2026-11-30"))
    database.add_new_data(target="transactions", new_data=transaction("t4", 7000, occurred_on="2026-12-01"))

    query = {"uid": "u1", "occurred_on": {"$gte": "2026-11-01", "$lt": "2026-12-01"}}
    rows = database.get_list_with_query(target="transactions", query=query, sort=[("occurred_on", -1), ("created_at", -1)])
    assert [row["transaction_id"] for row in rows] == ["t3", "t2"]
    assert rows[0]["merchant"] is None and rows[0]["receipt_id"] is None
    assert database.count_with_query(target="transactions", query=query) == 2
    assert database.count_with_query(target="transactions", query={"receipt_id": None}) == 4  # None 은 IS NULL
    assert database.count_with_query(target="transactions", query={"amount": {"$gt": 4500, "$lte": 9000}}) == 2


def test_sums(database):
    database.add_many_data(target="transactions", new_data_list=[
        transaction("t1", 9000, category="식비"),
        transaction("t2", 3000, category="생활"),
        transaction("t3", -3000, category="생활"),
        transaction("t4", 500000, category="급여", type="income"),
    ])
    expense = {"uid": "u1", "type": "expense"}
    assert database.get_sum(target="transactions", query=expense, sum_key="amount") == 9000
    assert database.get_sum(target="transactions", query={"uid": "nobody"}, sum_key="amount") == 0

    by_category = database.get_group_sums(target="transactions", query=expense, group_key="category", sum_key="amount")
    assert sorted(by_category, key=lambda row: row["key"]) == [
        {"key": "생활", "total": 0, "count": 2}, {"key": "식비", "total": 9000, "count": 1}]
    by_type = database.get_group_sums(target="transactions", query={"uid": "u1"}, group_key="type", sum_key="amount")
    assert {row["key"]: row["total"] for row in by_type} == {"expense": 9000, "income": 500000}


def test_modify_and_delete(database):
    database.add_new_data(target="transactions", new_data=transaction("t1", 9000))
    assert database.modify_data_with_query(target="transactions", query={"transaction_id": "t1", "uid": "u1"},
                                           new_data={"amount": 12000, "updated_at": NOW + timedelta(minutes=1)}) is True
    saved = database.get_data_with_key(target="transactions", key="transaction_id", key_data="t1")
    assert saved["amount"] == 12000
    assert saved["updated_at"] > saved["created_at"]
    assert database.modify_data_with_query(target="transactions", query={"transaction_id": "t1", "uid": "other"}, new_data={"amount": 1}) is False

    assert database.delete_data_with_query(target="transactions", query={"transaction_id": "t1", "uid": "other"}) is False
    assert database.delete_data_with_query(target="transactions", query={"transaction_id": "t1", "uid": "u1"}) is True
    assert database.count_with_query(target="transactions", query={}) == 0


def test_datetime_compare(database):
    # 영수증 정리·횟수 제한이 쓰는 시각 비교
    database.add_new_data(target="receipts", new_data=receipt("old", created_at=NOW - timedelta(hours=30)))
    database.add_new_data(target="receipts", new_data=receipt("new", created_at=NOW - timedelta(minutes=10)))
    recent = database.count_with_query(target="receipts", query={"uid": "u1", "created_at": {"$gte": NOW - timedelta(hours=1)}})
    assert recent == 1
    old = database.get_list_with_query(target="receipts", sort=[("created_at", 1)],
                                       query={"uid": "u1", "status": "analyzed", "created_at": {"$lt": NOW - timedelta(hours=24)}})
    assert [row["receipt_id"] for row in old] == ["old"]


def test_foreign_keys(database):
    # 없는 사용자·없는 카테고리·없는 영수증을 가리키는 내역은 넣을 수 없다
    for bad in [transaction("t1", 1000, uid="nobody"), transaction("t2", 1000, category="없는카테고리"),
                transaction("t3", 1000, receipt_id="no-receipt")]:
        with pytest.raises(DatabaseError):
            database.add_new_data(target="transactions", new_data=bad)
    assert database.count_with_query(target="transactions", query={}) == 0

    # 영수증을 지우면 그 영수증의 내역은 남고 연결만 끊긴다 (ON DELETE SET NULL)
    database.add_new_data(target="receipts", new_data=receipt("r1"))
    database.add_new_data(target="transactions", new_data=transaction("t4", 2800, receipt_id="r1"))
    database.delete_data_with_query(target="receipts", query={"receipt_id": "r1"})
    assert database.get_data_with_key(target="transactions", key="transaction_id", key_data="t4")["receipt_id"] is None


def test_add_many_is_all_or_nothing(database):
    rows = [transaction("t1", 1000), transaction("t2", 2000), transaction("t1", 3000)]  # 세 번째가 ID 중복
    with pytest.raises(DuplicateKeyError):
        database.add_many_data(target="transactions", new_data_list=rows)
    assert database.count_with_query(target="transactions", query={}) == 0


def test_withdraw_order_and_delete_all(database):
    database.add_new_data(target="users", new_data=user(uid="u2", email="other@yeongsugori.test"))
    database.add_new_data(target="receipts", new_data=receipt("r1"))
    database.add_new_data(target="transactions", new_data=transaction("t1", 2800, receipt_id="r1"))
    database.add_new_data(target="transactions", new_data=transaction("t2", 5000, uid="u2"))

    # 회원 탈퇴와 같은 순서: 내역 → 영수증 → 사용자
    for target in ["transactions", "receipts", "users"]:
        database.delete_all_data_with_key(target=target, key="uid", key_data="u1")
    assert database.count_with_query(target="users", query={}) == 1
    assert database.count_with_query(target="transactions", query={}) == 1  # 다른 사용자 내역은 남는다

    for target in ["transactions", "receipts", "users"]:
        database.delete_all_data(target=target)
    assert database.count_with_query(target="users", query={}) == 0


def test_unknown_names_are_rejected(database):
    # 테이블·컬럼·조건 기호는 정해진 것만 SQL 문에 들어간다
    with pytest.raises(DatabaseError):
        database.get_data_with_key(target="users; DROP TABLE users", key="uid", key_data="u1")
    with pytest.raises(DatabaseError):
        database.get_data_with_query(target="users", query={"uid = 'u1' OR 1=1 --": "x"})
    with pytest.raises(DatabaseError):
        database.count_with_query(target="users", query={"uid": {"$ne": "u1"}})
    assert database.count_with_query(target="users", query={}) == 1
