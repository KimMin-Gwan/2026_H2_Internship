# 연습 3: FastAPI 서버 처음 띄워 보기
# 실행 (이 폴더에서):  uvicorn practice_03_fastapi:app --reload --port 8100
# 확인: 브라우저에서 http://localhost:8100/docs  (여기서 API를 직접 눌러 볼 수 있다)
# 종료: 터미널에서 Ctrl + C

from typing import Optional

from fastapi import FastAPI

app = FastAPI()

# DB 대신 쓰는 리스트. 서버를 다시 켜면 초기화된다.
receipts = [
    {"receipt_id": "1", "store": "GS25", "amount": 3200, "category": "식비"},
    {"receipt_id": "2", "store": "스타벅스", "amount": 5500, "category": "카페·간식"},
    {"receipt_id": "3", "store": "지하철", "amount": 1500, "category": "교통"},
]


# 1) 가장 단순한 API: 주소로 들어오면 딕셔너리를 JSON으로 돌려준다.
@app.get("/api/hello")
def hello():
    return {"message": "안녕하세요"}


# 2) 쿼리 값 받기: /api/receipt/get_list?category=교통
@app.get("/api/receipt/get_list")
def get_list(category: Optional[str] = ""):
    if category:
        items = [r for r in receipts if r["category"] == category]
    else:
        items = receipts
    return {"items": items, "count": len(items)}


# 3) 본문(body) 받기: POST 로 JSON을 보내면 raw_request 에 딕셔너리로 들어온다.
@app.post("/api/receipt/create")
def create(raw_request: dict):
    body = raw_request.get("body", {})
    new_receipt = {
        "receipt_id": str(len(receipts) + 1),
        "store": str(body.get("store", "")),
        "amount": body.get("amount", 0),
        "category": str(body.get("category", "기타")),
    }
    receipts.append(new_receipt)
    return {"result": True, "item": new_receipt}


# 과제
# 1. /docs 에서 create 를 눌러 아래 JSON을 보내 보세요.
#    {"body": {"store": "CU", "amount": 4500, "category": "식비"}}
# 2. 이어서 get_list 를 눌러 방금 넣은 영수증이 보이는지 확인해 보세요.
# 3. /api/receipt/get_total 을 새로 만들어 amount 합계를 돌려주세요.
