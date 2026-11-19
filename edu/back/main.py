# FastAPI 실습용 서버 — Next.js 화면(edu/front/test-app)이 보낸 JSON을 받아서 JSON으로 답한다.
#
# 준비 (처음 한 번):  pip install fastapi uvicorn
# 실행 (이 폴더에서):  python main.py
# 확인:               http://localhost:8100/docs  (여기서 API를 직접 눌러 볼 수 있다)
# 종료:               터미널에서 Ctrl + C

import uvicorn
from fastapi import FastAPI

app = FastAPI()

# DB 대신 쓰는 리스트. 서버를 다시 켜면 처음 상태로 돌아간다.
receipts = [
    {"receipt_id": "1", "store": "GS25", "amount": 3200, "category": "식비"},
    {"receipt_id": "2", "store": "스타벅스", "amount": 5500, "category": "카페·간식"},
]


# 1) 가장 단순한 API: 이 주소로 들어오면 딕셔너리를 JSON으로 돌려준다.
@app.get("/api/hello")
def hello():
    return {"message": "안녕하세요"}


# 2) 목록 조회
@app.get("/api/receipt/get_list")
def get_list():
    return {"result": True, "items": receipts, "count": len(receipts)}


# 3) 화면이 보낸 JSON 받기: {"body": {"store": "CU", "amount": 4500, "category": "식비"}}
#    보낸 JSON이 raw_request 에 파이썬 딕셔너리로 들어온다.
@app.post("/api/receipt/create")
def create(raw_request: dict):
    body = raw_request.get("body", {})
    print("받은 데이터:", body)  # 터미널에서 화면이 보낸 값을 확인한다

    new_receipt = {
        "receipt_id": str(len(receipts) + 1),
        "store": str(body.get("store", "")),
        "amount": body.get("amount", 0),
        "category": str(body.get("category", "기타")),
    }
    receipts.append(new_receipt)
    return {"result": True, "detail": "저장되었습니다", "item": new_receipt, "count": len(receipts)}


# python main.py 로 직접 켤 때. 코드를 고치고 저장하면 자동으로 다시 켜진다(reload).
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8100, reload=True)
