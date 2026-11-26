# MongoDB 연결 — 모델은 이 클래스(또는 SQLite 용 Sql_Database)를 통해서만 DB에 접근한다. 돌려주는 문서에는 _id를 빼고 준다.
# 메서드 목록과 조건(query) 모양은 base_database.py 에 있다.

from pymongo import MongoClient
from pymongo import errors as mongo_errors

from models.database.base_database import Database
from models.database.errors import DatabaseError, DuplicateKeyError


class Mongo_Database(Database):
    def __init__(self, uri: str, db_name: str) -> None:
        # DB에 닿지 못할 때 오래 기다리지 않도록 5초만 기다린다. (Atlas 첫 연결은 DNS·TLS 때문에 1~2초 걸릴 수 있다)
        self.__client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.__db = self.__client[db_name]

    def ping(self) -> bool:
        try:
            return self.__db.command("ping")["ok"] == 1
        except mongo_errors.PyMongoError as error:
            raise DatabaseError(str(error))

    # 서버 시작 시 한 번 부른다. 이미 있는 인덱스는 그대로 둔다. (04 문서)
    def make_indexes(self) -> None:
        self.__db["users"].create_index("uid", unique=True)
        self.__db["users"].create_index("email", unique=True)
        self.__db["transactions"].create_index("transaction_id", unique=True)
        self.__db["transactions"].create_index([("uid", 1), ("occurred_on", -1)])
        self.__db["transactions"].create_index([("uid", 1), ("type", 1), ("category", 1), ("occurred_on", 1)])
        self.__db["transactions"].create_index("receipt_id")
        self.__db["receipts"].create_index("receipt_id", unique=True)
        self.__db["receipts"].create_index([("uid", 1), ("created_at", -1)])

    # target 컬렉션에서 key 값이 key_data 인 문서 하나. 없으면 None
    def get_data_with_key(self, target: str, key: str, key_data):
        return self.__db[target].find_one({key: key_data}, {"_id": 0})

    # 조건(query)에 맞는 문서 하나. 없으면 None
    def get_data_with_query(self, target: str, query: dict):
        return self.__db[target].find_one(query, {"_id": 0})

    # 조건에 맞는 문서 목록. sort 예: [("occurred_on", -1)]
    def get_list_with_query(self, target: str, query: dict, sort: list) -> list:
        return list(self.__db[target].find(query, {"_id": 0}).sort(sort))

    def count_with_query(self, target: str, query: dict) -> int:
        return self.__db[target].count_documents(query)

    # 조건에 맞는 문서의 sum_key 합계. SQL 의 SELECT SUM(...) WHERE ... 와 같다
    def get_sum(self, target: str, query: dict, sum_key: str) -> int:
        pipeline = [{"$match": query}, {"$group": {"_id": None, "total": {"$sum": f"${sum_key}"}}}]
        rows = list(self.__db[target].aggregate(pipeline))
        return rows[0]["total"] if rows else 0

    # group_key 값별 합계와 건수. SQL 의 SELECT ..., SUM(...), COUNT(*) ... GROUP BY 와 같다
    def get_group_sums(self, target: str, query: dict, group_key: str, sum_key: str) -> list:
        pipeline = [
            {"$match": query},
            {"$group": {"_id": f"${group_key}", "total": {"$sum": f"${sum_key}"}, "count": {"$sum": 1}}},
        ]
        return [{"key": row["_id"], "total": row["total"], "count": row["count"]} for row in self.__db[target].aggregate(pipeline)]

    def add_new_data(self, target: str, new_data: dict) -> None:
        try:
            # insert_one 은 넘긴 dict에 _id를 붙이므로 복사본을 넣는다.
            self.__db[target].insert_one(dict(new_data))
        except mongo_errors.DuplicateKeyError as error:
            raise DuplicateKeyError(str(error))

    # 여러 문서를 한 번에 넣는다 (영수증 품목 → 내역 일괄 저장)
    def add_many_data(self, target: str, new_data_list: list) -> None:
        self.__db[target].insert_many([dict(data) for data in new_data_list])

    # 조건에 맞는 문서 하나의 필드를 바꾼다. 맞는 문서가 없으면 False
    def modify_data_with_query(self, target: str, query: dict, new_data: dict) -> bool:
        return self.__db[target].update_one(query, {"$set": new_data}).matched_count == 1

    # 조건에 맞는 문서 하나를 지운다. 맞는 문서가 없으면 False
    def delete_data_with_query(self, target: str, query: dict) -> bool:
        return self.__db[target].delete_one(query).deleted_count == 1

    # key 값이 key_data 인 문서를 모두 지운다 (회원 탈퇴)
    def delete_all_data_with_key(self, target: str, key: str, key_data) -> None:
        self.__db[target].delete_many({key: key_data})

    # 컬렉션의 문서를 모두 지운다. 테스트에서 DB를 비울 때만 쓴다.
    def delete_all_data(self, target: str) -> None:
        self.__db[target].delete_many({})
