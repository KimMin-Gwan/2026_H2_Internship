# DB 오류 — MongoDB 든 SQLite 든 모델은 이 두 가지만 안다. 각 DB 클래스가 자기 오류를 이것으로 바꿔서 던진다.


class DatabaseError(Exception):
    pass


# unique 로 정한 값(이메일 등)이 이미 있을 때
class DuplicateKeyError(DatabaseError):
    pass
