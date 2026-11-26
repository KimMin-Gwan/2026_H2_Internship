# 분석 모델 — 월별 지출을 카테고리별로 묶고 비율, 전월 대비를 계산한다. 수입은 분석하지 않는다.
# 소비 조언은 그 달의 합계·카테고리·내역 전체를 AI에 보내 문장으로 받는다 (05 문서 9절).

import math

from models.base_model import BaseModel
from services.advice.client import make_advice
from services.advice.errors import AdviceError
from services.ocr.client import get_ocr_engine
from utils.date_util import is_valid_month, month_range, previous_month

# AI에 보내는 내역의 최대 개수 (최근 것부터)
MAX_ADVICE_ROWS = 300


class StatsModel(BaseModel):
    def __init__(self, database) -> None:
        super().__init__(database=database)
        self.__body = {}

    def get_category_stats(self, month: str) -> None:
        if not is_valid_month(month):
            self.set_fail(error_code="validation", detail="입력값이 올바르지 않습니다", fields={"month": "월을 확인하세요"})
            return

        total_expense = self.__get_total_expense(month=month)
        self.__body = {
            "month": month,
            "total_expense": total_expense,
            "prev_month_expense": self.__get_total_expense(month=previous_month(month)),
            "categories": self.__get_categories(month=month, total_expense=total_expense),
        }
        self.set_success()

    # 소비 조언. 그 달의 합계·카테고리·내역 전체를 AI에 보내고 요약과 조언을 문장으로 받는다. 결과는 저장하지 않는다.
    def analyze_spending(self, month: str) -> None:
        if not is_valid_month(month):
            self.set_fail(error_code="validation", detail="입력값이 올바르지 않습니다", fields={"month": "월을 확인하세요"})
            return

        start, end = month_range(month)
        rows = self._database.get_list_with_query(target="transactions",
                                                  query={"uid": self._user.uid, "occurred_on": {"$gte": start, "$lt": end}},
                                                  sort=[("occurred_on", -1), ("created_at", -1)])
        if not rows:
            self.set_fail(error_code="no_data", detail="분석할 내역이 없습니다")
            return

        total_expense = self.__get_total_expense(month=month)
        spending = {
            "month": month,
            "total_expense": total_expense,
            "total_income": sum(row["amount"] for row in rows if row["type"] == "income"),
            "prev_month_expense": self.__get_total_expense(month=previous_month(month)),
            "categories": self.__get_categories(month=month, total_expense=total_expense),
            # 계정 정보(uid, 이메일, 닉네임)와 ID는 보내지 않는다.
            "transactions": [
                {"date": row["occurred_on"], "type": row["type"], "category": row["category"], "title": row["title"],
                 "merchant": row.get("merchant"), "amount": row["amount"], "memo": row.get("memo", "")}
                for row in rows[:MAX_ADVICE_ROWS]
            ],
        }

        try:
            advice = make_advice(spending)
        except AdviceError as error:
            self.set_fail(error_code=error.code, detail=error.detail)
            return

        engine = get_ocr_engine()  # 어떤 AI가 쓴 글인지 화면에 보여 준다
        self.__body = {"month": month, "summary": advice["summary"], "advices": advice["advices"],
                       "ai_provider": engine["ocr_provider"], "ai_model": engine["ocr_model"]}
        self.set_success()

    def get_body_data(self) -> dict:
        return self.__body

    # 카테고리별 금액·건수·비율. 지출 합계가 0 이하이면 비율을 계산할 수 없으므로 빈 목록
    def __get_categories(self, month: str, total_expense: int) -> list:
        if total_expense <= 0:
            return []
        return [
            {"category": row["key"], "amount": row["total"], "count": row["count"],
             "ratio": self.__round_ratio(amount=row["total"], total=total_expense)}
            for row in self.__get_category_rows(month=month)
        ]

    # 내 지출 중 그 달의 것
    def __expense_query(self, month: str) -> dict:
        start, end = month_range(month)
        return {"uid": self._user.uid, "type": "expense", "occurred_on": {"$gte": start, "$lt": end}}

    # 한 달 지출 합계 (할인 같은 음수 금액 포함)
    def __get_total_expense(self, month: str) -> int:
        return self._database.get_sum(target="transactions", query=self.__expense_query(month), sum_key="amount")

    # 카테고리별 합계·건수. 0원 이하인 카테고리는 빼고, 금액이 큰 순서로(같으면 이름순) (04 문서 5절)
    def __get_category_rows(self, month: str) -> list:
        rows = self._database.get_group_sums(target="transactions", query=self.__expense_query(month),
                                             group_key="category", sum_key="amount")
        rows = [row for row in rows if row["total"] > 0]
        return sorted(rows, key=lambda row: (-row["total"], row["key"]))

    # 소수 첫째 자리 반올림. round()는 0.5를 짝수 쪽으로 보내므로 직접 계산한다.
    def __round_ratio(self, amount: int, total: int) -> float:
        return math.floor(amount * 1000 / total + 0.5) / 10
