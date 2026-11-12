# 연습용 코드

실행은 모두 이 폴더에서 한다. 번호 순서대로 진행한다.

| 파일 | 내용 | 실행 |
|---|---|---|
| practice_01_basics.py | 파이썬 기초 (변수, 리스트, 딕셔너리, 함수) | `python practice_01_basics.py` |
| practice_02_class.py | 클래스와 상속 | `python practice_02_class.py` |
| practice_03_fastapi.py | FastAPI 처음 띄우기 | `uvicorn practice_03_fastapi:app --reload --port 8100` |
| practice_04_mini_mvc.py | view · controller · model 흐름 | `uvicorn practice_04_mini_mvc:app --reload --port 8100` |
| practice_05_check.py | 서버 없이 API 확인 | `python practice_05_check.py` |

서버는 한 번에 하나만 띄운다 (포트 8100). 확인은 `http://localhost:8100/docs` 에서 한다.
`practice_` 로 시작하는 파일은 pytest 가 자동으로 실행하지 않는다.
