# 분석 — 로그인한 사용자를 넣은 모델을 만들고 월별 카테고리 통계, 소비 조언을 만들게 한다.

from models import Database, StatsModel
from utils import RequestManager


class Stats_Controller:
    def get_category_stats(self, database: Database, request: RequestManager) -> StatsModel:
        model = StatsModel(database=database)
        if not model.set_user_with_uid(uid=request.jwt_payload):
            return model

        model.get_category_stats(month=request.data_payload.month)
        return model

    # 그 달의 소비 데이터를 AI에 보내 조언을 받는다
    def try_analyze_spending(self, database: Database, request: RequestManager) -> StatsModel:
        model = StatsModel(database=database)
        if not model.set_user_with_uid(uid=request.jwt_payload):
            return model

        model.analyze_spending(month=request.data_payload.month)
        return model
