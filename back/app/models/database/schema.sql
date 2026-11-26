-- 영수고리 관계형 스키마 (SQLite). DB_TYPE=sqlite 일 때 서버가 시작하면서 실행한다 (08 문서).
-- 관계: users 1 : N receipts, users 1 : N transactions, receipts 1 : N transactions, categories 1 : N transactions

CREATE TABLE IF NOT EXISTS users (
  uid           VARCHAR(32)  NOT NULL PRIMARY KEY,
  email         VARCHAR(254) NOT NULL UNIQUE,
  password_hash VARCHAR(100) NOT NULL,
  nickname      VARCHAR(12)  NOT NULL,
  created_at    DATETIME     NOT NULL
);

-- 카테고리 목록. 서버 상수(others/constants.py)를 시작할 때 넣는다.
CREATE TABLE IF NOT EXISTS categories (
  name       VARCHAR(10) NOT NULL PRIMARY KEY,
  type       VARCHAR(7)  NOT NULL CHECK (type IN ('expense', 'income')),
  sort_order INT         NOT NULL
);

CREATE TABLE IF NOT EXISTS receipts (
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

CREATE TABLE IF NOT EXISTS transactions (
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

-- 자주 쓰는 조회에 맞춘 인덱스 (MongoDB 인덱스와 같은 구성)
CREATE INDEX IF NOT EXISTS idx_transactions_uid_day      ON transactions (uid, occurred_on DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_uid_category ON transactions (uid, type, category, occurred_on);
CREATE INDEX IF NOT EXISTS idx_transactions_receipt      ON transactions (receipt_id);
CREATE INDEX IF NOT EXISTS idx_receipts_uid_created      ON receipts (uid, created_at DESC);
