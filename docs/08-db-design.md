# 08. DB 설계 (관계형) 와 MongoDB 대응

이 프로젝트는 같은 데이터를 **두 가지 DB**에 저장할 수 있다. `.env` 의 `DB_TYPE` 으로 고른다.

| DB_TYPE | DB | 용도 |
|---|---|---|
| `mongo` (기본) | MongoDB (Atlas) | 슈퍼노바와 같은 구성. 04 문서 |
| `sqlite` | SQLite (관계형, 파일 하나) | 관계형 설계를 실제로 돌려 보는 구성. 이 문서 |

관계형 쪽은 설치가 필요 없는 **SQLite** 를 쓴다(파이썬 내장 `sqlite3`). 테이블 정의는 `back/app/models/database/schema.sql` 이고, 서버가 시작할 때 실행한다.
모델·컨트롤러·뷰 코드는 두 DB에서 같다. 다른 것은 DB 클래스 하나뿐이다 (6절).

## 1. ERD

![ERD](images/erd.png)

| 관계 | 의미 |
|---|---|
| users 1 : N receipts | 한 사용자가 영수증을 여러 장 올린다 |
| users 1 : N transactions | 한 사용자가 내역을 여러 건 가진다 |
| receipts 1 : N transactions | 영수증 한 장의 품목이 내역 여러 건이 된다 (직접 입력한 내역은 `receipt_id` 가 비어 있다) |
| categories 1 : N transactions | 내역은 카테고리 하나에 속한다 |

영수증 품목을 따로 저장하는 테이블은 두지 않는다. 사용자가 확인·저장한 품목은 곧바로 `transactions` 의 행이 된다.
분석이 끝난 직후의 품목 목록은 `receipts.parsed_json` (원문)에서 만든다.

## 2. 테이블 정의 (SQL)

`schema.sql` 의 내용이다. 서버가 `CREATE TABLE IF NOT EXISTS` 로 만들므로 이미 있으면 그대로 둔다.

```sql
CREATE TABLE users (
  uid           VARCHAR(32)  NOT NULL PRIMARY KEY,
  email         VARCHAR(254) NOT NULL UNIQUE,
  password_hash VARCHAR(100) NOT NULL,
  nickname      VARCHAR(12)  NOT NULL,
  created_at    DATETIME     NOT NULL
);

CREATE TABLE categories (
  name       VARCHAR(10) NOT NULL PRIMARY KEY,
  type       VARCHAR(7)  NOT NULL CHECK (type IN ('expense', 'income')),
  sort_order INT         NOT NULL
);

CREATE TABLE receipts (
  receipt_id   VARCHAR(32)  NOT NULL PRIMARY KEY,
  uid          VARCHAR(32)  NOT NULL,
  image_key    VARCHAR(200) NOT NULL,
  status       VARCHAR(9)   NOT NULL CHECK (status IN ('analyzed', 'confirmed')),
  merchant     VARCHAR(50)  NULL,
  purchased_on DATE         NULL,
  total_amount INT          NULL,
  parsed_json  TEXT         NOT NULL,          -- 모델이 돌려준 JSON 원문
  confidence   VARCHAR(6)   NOT NULL,          -- high, medium, low
  ocr_provider VARCHAR(10)  NOT NULL,          -- 분석한 AI: mock, openai, claude
  ocr_model    VARCHAR(50)  NOT NULL,
  created_at   DATETIME     NOT NULL,
  FOREIGN KEY (uid) REFERENCES users(uid) ON DELETE CASCADE
);

CREATE TABLE transactions (
  transaction_id VARCHAR(32)  NOT NULL PRIMARY KEY,
  uid            VARCHAR(32)  NOT NULL,
  type           VARCHAR(7)   NOT NULL CHECK (type IN ('expense', 'income')),
  amount         INT          NOT NULL,        -- 원 단위. 영수증 할인 품목만 음수
  category       VARCHAR(10)  NOT NULL,
  title          VARCHAR(40)  NOT NULL,
  merchant       VARCHAR(50)  NULL,            -- 영수증 내역만
  memo           VARCHAR(100) NOT NULL,
  occurred_on    DATE         NOT NULL,
  receipt_id     VARCHAR(32)  NULL,            -- 영수증 연결 내역만
  created_at     DATETIME     NOT NULL,
  updated_at     DATETIME     NOT NULL,
  FOREIGN KEY (uid)        REFERENCES users(uid)           ON DELETE CASCADE,
  FOREIGN KEY (category)   REFERENCES categories(name),
  FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id) ON DELETE SET NULL
);

CREATE INDEX idx_transactions_uid_day      ON transactions (uid, occurred_on DESC);
CREATE INDEX idx_transactions_uid_category ON transactions (uid, type, category, occurred_on);
CREATE INDEX idx_transactions_receipt      ON transactions (receipt_id);
CREATE INDEX idx_receipts_uid_created      ON receipts (uid, created_at DESC);
```

- **기본 키는 문자열 ID** 다(`uid`, `transaction_id`, `receipt_id`). 서버가 `uuid4().hex` 로 만든다. 자동 증가 숫자(`AUTO_INCREMENT`)를 쓰지 않은 이유: MongoDB 구현과 같은 ID를 써야 모델 코드가 하나로 유지되고, ID를 DB가 아니라 서버가 정하므로 두 DB의 동작이 같다.
- `categories` 의 기본 키는 이름(`name`)이다. 값은 04 문서 4절의 12개(지출 9, 수입 3)이고 서버가 시작할 때 상수에서 채운다. `transactions.category` 가 이 테이블을 가리키므로 목록에 없는 카테고리는 DB가 거부한다.
- SQLite는 `VARCHAR(n)` 의 길이와 `DATE`·`DATETIME` 타입을 강제하지 않는다(글자로 저장한다). 길이·형식 검증은 모델이 한다. 날짜는 `YYYY-MM-DD`, 시각은 UTC `YYYY-MM-DD HH:MM:SS.ffffff` 문자열이라 문자열 비교가 곧 시간 순서다.
- 로그인 상태는 JWT 쿠키에 담기므로(서버에 저장하지 않음) 세션 테이블은 두지 않는다.

## 3. 대응표 (관계형 ↔ MongoDB)

| 관계형 (SQLite) | MongoDB |
|---|---|
| 테이블 `users`, `receipts`, `transactions` | 같은 이름의 컬렉션 3개 |
| 테이블 `categories` | **컬렉션 없음.** 서버 상수 목록(04 문서 4절). 카테고리 이름 문자열을 그대로 저장 |
| 기본 키 `uid`, `transaction_id`, `receipt_id` | 같은 이름의 문자열 필드 + unique 인덱스. `_id` 는 쓰지 않는다 |
| 외래 키 `uid`, `receipt_id`, `category` (DB가 검사) | 같은 이름의 필드. **DB가 검사하지 않으므로** 서버 코드가 소유자·카테고리를 확인한다 |
| `DATE`, `DATETIME` (문자열로 저장) | `"YYYY-MM-DD"` 문자열, UTC `datetime` |
| `UNIQUE` | unique 인덱스 (`users.email`, 각 컬렉션의 ID 필드) |
| `ON DELETE CASCADE` | 없음. 회원 탈퇴 때 서버가 `transactions` → `receipts`(이미지 파일 포함) → `users` 순서로 지운다. SQLite에서도 같은 순서로 지우므로 결과가 같다 |
| `ON DELETE SET NULL` | 없음 (영수증은 탈퇴와 24시간 정리 때만 지워진다) |
| 여러 행을 한 트랜잭션으로 저장 (전부 저장 또는 전부 취소) | `insert_many` (중간에 실패하면 앞의 것은 남을 수 있다) |
| 인덱스 4개 | 04 문서 각 컬렉션 절의 인덱스 |

수업 포인트: 관계형은 카테고리를 테이블로 두고 외래 키로 잘못된 값을 막는다. MongoDB는 이름을 문서에 직접 넣고 검사를 서버 코드에 맡긴다.
같은 기능을 두 방식으로 만들어 보면 "DB가 지켜 주는 것"과 "코드가 지켜야 하는 것"의 차이가 보인다.

## 4. 같은 질문, 두 가지 쿼리

모델은 DB 객체의 메서드만 부른다. 아래는 그 메서드가 각 DB에서 실행하는 내용이다.

월별 요약 (`get_group_sums(target="transactions", group_key="type", sum_key="amount", query=...)`):

```sql
SELECT type AS key, SUM(amount) AS total, COUNT(*) AS count
FROM transactions
WHERE uid = ? AND occurred_on >= ? AND occurred_on < ?
GROUP BY type;
```
```
db.transactions.aggregate([
  { $match: { uid, occurred_on: { $gte: start, $lt: next } } },
  { $group: { _id: "$type", total: { $sum: "$amount" }, count: { $sum: 1 } } }
])
```

카테고리 통계(지출) (`get_group_sums(..., group_key="category", ...)`). 0원 이하 카테고리를 빼고 금액순으로 정렬하는 일은 모델이 한다:

```sql
SELECT category AS key, SUM(amount) AS total, COUNT(*) AS count
FROM transactions
WHERE uid = ? AND type = ? AND occurred_on >= ? AND occurred_on < ?
GROUP BY category;
```
```
db.transactions.aggregate([
  { $match: { uid, type: "expense", occurred_on: { $gte: start, $lt: next } } },
  { $group: { _id: "$category", total: { $sum: "$amount" }, count: { $sum: 1 } } }
])
```

카테고리 표시 순서까지 DB에서 가져오려면 `JOIN` 을 쓴다 (코드에는 없고, 연습용 예시다):

```sql
SELECT c.name, COALESCE(SUM(t.amount), 0) AS total
FROM categories c
LEFT JOIN transactions t ON t.category = c.name AND t.uid = ? AND t.occurred_on >= ? AND t.occurred_on < ?
WHERE c.type = 'expense'
GROUP BY c.name
ORDER BY c.sort_order;
```

## 5. 학생 과제 (설계 단계)

1. ERD를 직접 그린다 (도구 자유). 1절 그림은 정답이 아니라 예시이다.
2. 요구 기능 목록(02 문서)에서 테이블과 컬럼을 뽑아 본다.
3. 카테고리를 테이블로 분리한 이유와 문자열로 두었을 때의 장단점을 한 문단으로 쓴다.
4. `DB_TYPE=sqlite` 로 서버를 켜고 내역을 몇 건 넣은 뒤, DB 파일을 열어 4절의 SQL을 직접 실행해 본다 (7절).

## 6. 코드 구조 (`back/app/models/database/`)

| 파일 | 내용 |
|---|---|
| `base_database.py` | `Database`: 모델이 DB에 시킬 수 있는 일의 목록(메서드 14개)과 조건(query) 모양 |
| `database_model.py` | `Mongo_Database(Database)`: MongoDB 로 구현 |
| `sql_database_model.py` | `Sql_Database(Database)`: SQL 문으로 구현. 조건(dict)을 `WHERE` 절로 바꾼다 |
| `schema.sql` | 테이블·인덱스 정의 (2절) |
| `database_factory.py` | `make_database()`: `DB_TYPE` 을 보고 둘 중 하나를 만든다 |
| `errors.py` | `DatabaseError`, `DuplicateKeyError`: 두 DB의 오류를 같은 이름으로 맞춘다 |

- 모델은 조건을 `{"uid": "...", "occurred_on": {"$gte": 시작, "$lt": 끝}}` 모양으로 넘긴다. `Sql_Database` 가 이것을 `WHERE uid = ? AND occurred_on >= ? AND occurred_on < ?` 로 바꾼다.
- 값은 항상 `?` 자리에 따로 넘긴다(SQL 삽입 방지). 테이블·컬럼 이름은 `?` 로 넘길 수 없으므로 정해진 목록(`COLUMNS`)에 있는 것만 쓴다.
- OOP 수업 연결: 부모 클래스 하나(`Database`)에 자식 둘이 같은 메서드를 다르게 구현하고, 모델은 어느 쪽인지 모른 채 호출한다 (상속과 다형성).

## 7. SQLite로 켜기

```
# .env
DB_TYPE=sqlite
```

- docker: `docker compose up --build`. DB 파일은 `sqlite_data` 볼륨의 `/data/db/yeongsugori.db`.
- 개발 서버: `cd back/app && ../.venv/Scripts/python main.py`. DB 파일은 `back/data/yeongsugori.db` (깃에 올리지 않는다).
- 데모 데이터: `python -m scripts.seed` (docker: `docker compose exec back python -m scripts.seed`).
- 파일 열어 보기: VS Code 확장 "SQLite Viewer" 나 DB Browser for SQLite 로 `yeongsugori.db` 를 연다.
- 테스트: `$env:DB_TYPE="sqlite"; .venv/Scripts/pytest` (임시 파일을 쓴다). `tests/test_sql_database.py` 는 `DB_TYPE` 과 상관없이 SQLite 클래스를 확인한다.
- MongoDB와 SQLite의 데이터는 서로 옮겨지지 않는다. `DB_TYPE` 을 바꾸면 빈 DB에서 시작한다(가입부터 다시).
