# 연습 4: 작은 MVC — 실제 서버(views / controllers / models)와 같은 흐름을 한 파일에 담았다.
# 실행 (이 폴더에서):  uvicorn practice_04_mini_mvc:app --reload --port 8100
# 확인: http://localhost:8100/docs
#
# 요청 흐름:  view(경로로 받음) → controller(모델을 만들어 실행) → model(검증·데이터 처리) → view(JSON으로 응답)

from typing import Optional

from fastapi import FastAPI


# ---------- model: 데이터와 규칙 ----------
class BaseModel:
    def __init__(self):
        self._result = False
        self._detail = ""
        self._error_code = ""

    def set_success(self, detail=""):
        self._result = True
        self._detail = detail

    def set_fail(self, error_code, detail):
        self._result = False
        self._error_code = error_code
        self._detail = detail

    def get_body_data(self):      # 자식 모델이 다시 정의한다.
        return {}

    def get_response_form_data(self):
        body = {"result": self._result, "detail": self._detail}
        if not self._result:
            body["error_code"] = self._error_code
        body.update(self.get_body_data())
        return {"header": {}, "body": body}


class ReceiptModel(BaseModel):
    def __init__(self, database):
        super().__init__()
        self._database = database   # DB 대신 리스트
        self.__body = {}

    def get_list(self, category):
        items = [r for r in self._database if not category or r["category"] == category]
        self.__body = {"items": items}
        self.set_success()

    def create(self, store, amount, category):
        if store.strip() == "":
            self.set_fail("validation", "가게 이름을 입력하세요")
            return
        if not isinstance(amount, int) or amount <= 0:
            self.set_fail("validation", "금액을 확인하세요")
            return
        item = {"receipt_id": str(len(self._database) + 1), "store": store, "amount": amount, "category": category}
        self._database.append(item)
        self.__body = {"item": item}
        self.set_success("저장되었습니다")

    def get_body_data(self):
        return self.__body


# ---------- controller: view 와 model 을 이어 준다 ----------
class Receipt_Controller:
    def get_list(self, database, category):
        model = ReceiptModel(database=database)
        model.get_list(category=category)
        return model

    def try_create(self, database, store, amount, category):
        model = ReceiptModel(database=database)
        model.create(store=store, amount=amount, category=category)
        return model


# ---------- view: API 경로와 입출구 ----------
app = FastAPI()
database = [
    {"receipt_id": "1", "store": "GS25", "amount": 3200, "category": "식비"},
    {"receipt_id": "2", "store": "스타벅스", "amount": 5500, "category": "카페·간식"},
]


@app.get("/api/receipt/get_list")
def get_list(category: Optional[str] = ""):
    model = Receipt_Controller().get_list(database=database, category=category)
    return model.get_response_form_data()


@app.post("/api/receipt/create")
def create(raw_request: dict):
    body = raw_request.get("body", {})
    model = Receipt_Controller().try_create(database=database, store=str(body.get("store", "")),
                                            amount=body.get("amount", 0), category=str(body.get("category", "기타")))
    return model.get_response_form_data()


# 과제
# 1. ReceiptModel 에 delete(receipt_id) 를 만들고, controller 와 view 에 /api/receipt/delete 를 이어 보세요.
#    (없는 id 는 set_fail("not_found", "영수증을 찾을 수 없습니다"))
# 2. 어느 단계를 고쳤는지 말해 보세요: 검증 문구 변경 → model, 경로 이름 변경 → view.
