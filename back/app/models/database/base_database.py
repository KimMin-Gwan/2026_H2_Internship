# DB 클래스의 부모 — 모델이 DB에 시킬 수 있는 일의 목록이다. MongoDB 용과 SQLite 용이 각자 구현한다.
# 모델은 어느 DB인지 모르고 같은 메서드를 부른다 (.env 의 DB_TYPE 으로 고른다, 04·08 문서).
#
# 조건(query)은 두 DB가 같은 모양으로 받는다.
#   {"uid": "abc"}                                    uid 가 abc 인 것
#   {"uid": "abc", "type": "expense"}                 둘 다 맞는 것 (AND)
#   {"occurred_on": {"$gte": "2026-11-01", "$lt": "2026-12-01"}}   범위. $gt(초과) $gte(이상) $lt(미만) $lte(이하)
# target 은 MongoDB 에서는 컬렉션, SQLite 에서는 테이블 이름이다 (users, transactions, receipts).


class Database:
    def ping(self) -> bool:
        raise NotImplementedError

    # 서버 시작 시 한 번 부른다. MongoDB 는 인덱스를, SQLite 는 테이블과 인덱스를 만든다. 이미 있으면 그대로 둔다.
    def make_indexes(self) -> None:
        raise NotImplementedError

    # key 값이 key_data 인 데이터 하나(dict). 없으면 None
    def get_data_with_key(self, target: str, key: str, key_data):
        raise NotImplementedError

    # 조건에 맞는 데이터 하나(dict). 없으면 None
    def get_data_with_query(self, target: str, query: dict):
        raise NotImplementedError

    # 조건에 맞는 데이터 목록. sort 예: [("occurred_on", -1)] (1 오름차순, -1 내림차순)
    def get_list_with_query(self, target: str, query: dict, sort: list) -> list:
        raise NotImplementedError

    def count_with_query(self, target: str, query: dict) -> int:
        raise NotImplementedError

    # 조건에 맞는 데이터의 sum_key 합계. 맞는 것이 없으면 0
    def get_sum(self, target: str, query: dict, sum_key: str) -> int:
        raise NotImplementedError

    # 조건에 맞는 데이터를 group_key 값별로 묶은 합계와 건수: [{"key": 값, "total": 합계, "count": 건수}, ...]
    def get_group_sums(self, target: str, query: dict, group_key: str, sum_key: str) -> list:
        raise NotImplementedError

    # unique 값이 이미 있으면 DuplicateKeyError
    def add_new_data(self, target: str, new_data: dict) -> None:
        raise NotImplementedError

    # 여러 데이터를 한 번에 넣는다 (영수증 품목 → 내역 일괄 저장)
    def add_many_data(self, target: str, new_data_list: list) -> None:
        raise NotImplementedError

    # 조건에 맞는 데이터 하나의 값을 바꾼다. 맞는 것이 없으면 False
    def modify_data_with_query(self, target: str, query: dict, new_data: dict) -> bool:
        raise NotImplementedError

    # 조건에 맞는 데이터 하나를 지운다. 맞는 것이 없으면 False
    def delete_data_with_query(self, target: str, query: dict) -> bool:
        raise NotImplementedError

    # key 값이 key_data 인 데이터를 모두 지운다 (회원 탈퇴)
    def delete_all_data_with_key(self, target: str, key: str, key_data) -> None:
        raise NotImplementedError

    # target 의 데이터를 모두 지운다. 테스트에서 DB를 비울 때만 쓴다.
    def delete_all_data(self, target: str) -> None:
        raise NotImplementedError
