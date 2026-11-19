# 연습 2: 클래스와 상속 (OOP)
# 실행: python practice_02_class.py
# C++의 class와 같은 개념이다. this 대신 self 를 쓰고, 생성자는 __init__ 이다.


class Receipt:
    def __init__(self, store, amount):
        self.store = store      # 속성
        self.amount = amount

    def get_summary(self):      # 메서드
        return f"{self.store} {self.amount}원"

    def get_fee(self):
        return 0


# 상속: Receipt 의 기능을 물려받고 다른 부분만 다시 정의한다.
class CardReceipt(Receipt):
    def __init__(self, store, amount, card_name):
        super().__init__(store, amount)   # 부모의 __init__ 호출
        self.card_name = card_name

    def get_summary(self):
        return f"{self.store} {self.amount}원 ({self.card_name})"

    def get_fee(self):
        return int(self.amount * 0.01)    # 카드 수수료 1% 라고 가정


class CashReceipt(Receipt):
    def get_summary(self):
        return f"{self.store} {self.amount}원 (현금)"


# 다형성: 종류가 달라도 같은 이름(get_summary)으로 호출한다.
receipts = [
    Receipt("GS25", 3200),
    CardReceipt("스타벅스", 5500, "신한카드"),
    CashReceipt("붕어빵 노점", 2000),
]
for r in receipts:
    print(r.get_summary(), "/ 수수료", r.get_fee())


# 서버 코드에서도 같은 구조를 쓴다: 모든 모델이 BaseModel 을 상속한다.
class BaseModel:
    def __init__(self):
        self._result = False
        self._detail = ""

    def set_success(self, detail=""):
        self._result = True
        self._detail = detail

    def get_response_form_data(self):
        return {"result": self._result, "detail": self._detail}


class ReceiptModel(BaseModel):
    def create(self, store, amount):
        if amount <= 0:
            self._detail = "금액을 확인하세요"
            return
        self.set_success("저장되었습니다")


model = ReceiptModel()
model.create("GS25", 3200)
print(model.get_response_form_data())
