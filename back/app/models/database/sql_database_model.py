# SQLite 연결 — Mongo_Database 와 같은 메서드를 SQL 문으로 구현한다 (DB_TYPE=sqlite).
# 테이블은 schema.sql 로 만든다. 값은 항상 ? 자리에 따로 넘긴다(SQL 문에 값을 직접 붙이지 않는다).

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from models.database.base_database import Database
from models.database.errors import DatabaseError, DuplicateKeyError
from others.constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES

SCHEMA_FILE = Path(__file__).with_name("schema.sql")

# 테이블마다 쓸 수 있는 컬럼. 컬럼 이름은 ? 로 넘길 수 없으므로 SQL 문에 넣기 전에 이 목록으로 확인한다.
COLUMNS = {
    "users": ["uid", "email", "password_hash", "nickname", "created_at"],
    "categories": ["name", "type", "sort_order"],
    "receipts": ["receipt_id", "uid", "image_key", "status", "merchant", "purchased_on", "total_amount", "parsed_json",
                 "confidence", "ocr_provider", "ocr_model", "created_at"],
    "transactions": ["transaction_id", "uid", "type", "amount", "category", "title", "merchant", "memo", "occurred_on",
                     "receipt_id", "created_at", "updated_at"],
}
# 시각은 "2026-11-02 05:21:00.000000" 같은 문자열(UTC)로 저장하고, 읽을 때 datetime 으로 되돌린다.
DATETIME_COLUMNS = ["created_at", "updated_at"]
# 조건의 범위 표시를 SQL 비교 기호로 바꾼다.
OPERATORS = {"$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}


class Sql_Database(Database):
    def __init__(self, path: str) -> None:
        self.__path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def ping(self) -> bool:
        return self.__read("SELECT 1 AS ok", [])[0]["ok"] == 1

    # 테이블·인덱스를 만들고(이미 있으면 그대로) 카테고리 목록을 채운다.
    def make_indexes(self) -> None:
        try:
            with closing(self.__connect()) as connection, connection:
                connection.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
                rows = [(name, "expense", order) for order, name in enumerate(EXPENSE_CATEGORIES)]
                rows += [(name, "income", order) for order, name in enumerate(INCOME_CATEGORIES)]
                connection.executemany("INSERT OR IGNORE INTO categories (name, type, sort_order) VALUES (?, ?, ?)", rows)
        except sqlite3.Error as error:
            raise DatabaseError(str(error))

    def get_data_with_key(self, target: str, key: str, key_data):
        return self.get_data_with_query(target=target, query={key: key_data})

    def get_data_with_query(self, target: str, query: dict):
        where, params = self.__where(target, query)
        rows = self.__read(f"SELECT * FROM {self.__table(target)}{where} LIMIT 1", params)
        return rows[0] if rows else None

    def get_list_with_query(self, target: str, query: dict, sort: list) -> list:
        where, params = self.__where(target, query)
        order = ", ".join(f"{self.__column(target, key)} {'DESC' if direction == -1 else 'ASC'}" for key, direction in sort)
        order_by = f" ORDER BY {order}" if order else ""
        return self.__read(f"SELECT * FROM {self.__table(target)}{where}{order_by}", params)

    def count_with_query(self, target: str, query: dict) -> int:
        where, params = self.__where(target, query)
        return self.__read(f"SELECT COUNT(*) AS count FROM {self.__table(target)}{where}", params)[0]["count"]

    def get_sum(self, target: str, query: dict, sum_key: str) -> int:
        where, params = self.__where(target, query)
        sql = f"SELECT COALESCE(SUM({self.__column(target, sum_key)}), 0) AS total FROM {self.__table(target)}{where}"
        return self.__read(sql, params)[0]["total"]

    def get_group_sums(self, target: str, query: dict, group_key: str, sum_key: str) -> list:
        where, params = self.__where(target, query)
        group = self.__column(target, group_key)
        sql = (f"SELECT {group} AS key, SUM({self.__column(target, sum_key)}) AS total, COUNT(*) AS count "
               f"FROM {self.__table(target)}{where} GROUP BY {group}")
        return self.__read(sql, params)

    def add_new_data(self, target: str, new_data: dict) -> None:
        self.__write(self.__insert_sql(target, list(new_data)), [self.__values(new_data)])

    # 한 번의 트랜잭션으로 넣는다. 하나라도 실패하면 전부 취소된다.
    def add_many_data(self, target: str, new_data_list: list) -> None:
        if not new_data_list:
            return
        keys = list(new_data_list[0])
        self.__write(self.__insert_sql(target, keys), [self.__values({key: data[key] for key in keys}) for data in new_data_list])

    def modify_data_with_query(self, target: str, query: dict, new_data: dict) -> bool:
        where, params = self.__where(target, query)
        sets = ", ".join(f"{self.__column(target, key)} = ?" for key in new_data)
        return self.__write(f"UPDATE {self.__table(target)} SET {sets}{where}", [self.__values(new_data) + params]) == 1

    def delete_data_with_query(self, target: str, query: dict) -> bool:
        where, params = self.__where(target, query)
        return self.__write(f"DELETE FROM {self.__table(target)}{where}", [params]) == 1

    def delete_all_data_with_key(self, target: str, key: str, key_data) -> None:
        where, params = self.__where(target, {key: key_data})
        self.__write(f"DELETE FROM {self.__table(target)}{where}", [params])

    def delete_all_data(self, target: str) -> None:
        self.__write(f"DELETE FROM {self.__table(target)}", [[]])

    # ── 아래는 이 클래스 안에서만 쓴다 ──

    # 부를 때마다 새로 연결한다. SQLite 는 파일 하나라서 연결이 가볍고, 요청이 여러 스레드에서 와도 안전하다.
    def __connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.__path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")  # 외래 키 검사는 연결마다 켜야 한다
        return connection

    # SELECT 를 실행하고 결과를 dict 목록으로 돌려준다.
    def __read(self, sql: str, params: list) -> list:
        try:
            with closing(self.__connect()) as connection:
                return [self.__to_dict(row) for row in connection.execute(sql, params).fetchall()]
        except sqlite3.Error as error:
            raise DatabaseError(str(error))

    # INSERT·UPDATE·DELETE 를 한 트랜잭션으로 실행하고 바뀐 행 수를 돌려준다. params_list 는 실행할 값 묶음의 목록
    def __write(self, sql: str, params_list: list) -> int:
        try:
            with closing(self.__connect()) as connection, connection:
                return connection.executemany(sql, params_list).rowcount
        except sqlite3.IntegrityError as error:
            if "UNIQUE" in str(error):
                raise DuplicateKeyError(str(error))
            raise DatabaseError(str(error))
        except sqlite3.Error as error:
            raise DatabaseError(str(error))

    def __table(self, target: str) -> str:
        if target not in COLUMNS:
            raise DatabaseError(f"없는 테이블입니다: {target}")
        return target

    def __column(self, target: str, key: str) -> str:
        if key not in COLUMNS[self.__table(target)]:
            raise DatabaseError(f"{target} 테이블에 없는 컬럼입니다: {key}")
        return key

    def __insert_sql(self, target: str, keys: list) -> str:
        columns = ", ".join(self.__column(target, key) for key in keys)
        marks = ", ".join("?" for _ in keys)
        return f"INSERT INTO {self.__table(target)} ({columns}) VALUES ({marks})"

    # 조건(dict)을 WHERE 절과 값 목록으로 바꾼다. 예: {"uid": "a", "occurred_on": {"$gte": "2026-11-01"}}
    #   → (" WHERE uid = ? AND occurred_on >= ?", ["a", "2026-11-01"])
    def __where(self, target: str, query: dict):
        parts, params = [], []
        for key, value in query.items():
            column = self.__column(target, key)
            if isinstance(value, dict):
                for operator, operand in value.items():
                    if operator not in OPERATORS:
                        raise DatabaseError(f"쓸 수 없는 조건입니다: {operator}")
                    parts.append(f"{column} {OPERATORS[operator]} ?")
                    params.append(self.__value(operand))
            elif value is None:
                parts.append(f"{column} IS NULL")
            else:
                parts.append(f"{column} = ?")
                params.append(self.__value(value))
        return (" WHERE " + " AND ".join(parts) if parts else ""), params

    def __values(self, data: dict) -> list:
        return [self.__value(value) for value in data.values()]

    # 파이썬 값을 DB에 넣을 값으로. 시각은 UTC 문자열로 바꾼다 (문자열끼리 비교해도 시간 순서가 맞는다).
    def __value(self, value):
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            return value.isoformat(sep=" ", timespec="microseconds")
        return value

    # DB의 한 행을 dict 로. 시각 문자열은 datetime 으로 되돌린다 (MongoDB 가 돌려주는 모양과 같게).
    def __to_dict(self, row: sqlite3.Row) -> dict:
        data = dict(row)
        for key in DATETIME_COLUMNS:
            if isinstance(data.get(key), str):
                data[key] = datetime.fromisoformat(data[key])
        return data
