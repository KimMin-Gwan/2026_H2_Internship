# DB 고르기 — .env 의 DB_TYPE 에 따라 MongoDB 또는 SQLite 용 DB 객체를 만든다. 모델은 어느 쪽인지 몰라도 된다.

from models.database.base_database import Database
from models.database.database_model import Mongo_Database
from models.database.sql_database_model import Sql_Database
from others import config


def make_database() -> Database:
    if config.DB_TYPE == "sqlite":
        return Sql_Database(path=config.SQLITE_PATH)
    return Mongo_Database(uri=config.MONGODB_URI, db_name=config.MONGODB_DB)
