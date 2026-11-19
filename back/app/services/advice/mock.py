# mock 조언 — 모델을 부르지 않고 받은 숫자로 예시 문장을 만든다. 키 없이 시연·테스트할 때 쓴다.
# 결과 모양은 실제 모델 출력(schema.py)과 같다.

import time

# 진행 표시를 볼 수 있도록 잠깐 기다린다. 테스트에서는 0으로 바꾼다.
DELAY_SEC = 1.0


def advise(spending: dict) -> dict:
    time.sleep(DELAY_SEC)
    summary = f"이번 달 지출은 {spending['total_expense']:,}원입니다."
    if spending["categories"]:
        top = spending["categories"][0]
        summary += f" {top['category']} 지출이 {top['amount']:,}원({top['ratio']}%)으로 가장 큽니다."
    return {
        "summary": summary,
        "advices": [
            "지출이 가장 큰 카테고리는 주 단위 예산을 정해 두시기 바랍니다.",
            "소액 결제가 잦은 항목은 금액보다 횟수를 먼저 줄여 보시기 바랍니다.",
            "고정 지출과 변동 지출을 나누어 기록하면 다음 달 계획을 세우기 쉽습니다.",
        ],
    }
