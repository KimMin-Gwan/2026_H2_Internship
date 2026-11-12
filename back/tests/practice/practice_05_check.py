# 연습 5: 서버를 띄우지 않고 API가 맞게 동작하는지 확인하기
# 실행 (이 폴더에서):  python practice_05_check.py
# practice_04 의 API를 코드로 직접 호출해서 결과를 비교한다. 틀리면 AssertionError 가 난다.

from fastapi.testclient import TestClient

from practice_04_mini_mvc import app

client = TestClient(app)


def check_get_list():
    res = client.get("/api/receipt/get_list")
    assert res.status_code == 200
    assert res.json()["body"]["result"] is True
    assert len(res.json()["body"]["items"]) == 2


def check_category_filter():
    res = client.get("/api/receipt/get_list", params={"category": "식비"})
    items = res.json()["body"]["items"]
    assert len(items) == 1 and items[0]["store"] == "GS25"


def check_create_ok():
    res = client.post("/api/receipt/create", json={"body": {"store": "CU", "amount": 4500, "category": "식비"}})
    assert res.json()["body"]["result"] is True


def check_create_fail():
    res = client.post("/api/receipt/create", json={"body": {"store": "", "amount": 4500}})
    body = res.json()["body"]
    assert body["result"] is False
    assert body["error_code"] == "validation"


for func in (check_get_list, check_category_filter, check_create_ok, check_create_fail):
    func()
    print("통과:", func.__name__)

# 과제: 금액이 0 이하일 때 실패하는지 확인하는 check_create_zero_amount 를 추가해 보세요.
