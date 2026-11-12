# 연습 1: 파이썬 기초
# 실행: python practice_01_basics.py
# C++와 다른 점: 중괄호 { } 대신 들여쓰기(공백 4칸)로 블록을 나눈다. 변수 타입은 적지 않는다. 줄 끝에 ; 가 없다.

# 1) 변수
store = "GS25"
amount = 3200
is_card = True

# 2) 출력과 f-string: 문자열 앞에 f 를 붙이면 { } 안에 변수를 넣을 수 있다.
print(f"{store}에서 {amount}원 결제")

# 3) 리스트 (C++의 vector와 비슷)
amounts = [3200, 5500, 12000]
amounts.append(800)
print("합계:", sum(amounts), "건수:", len(amounts))

# 4) 딕셔너리: 이름표(key)로 값을 꺼낸다. JSON과 모양이 같다.
receipt = {"store": "GS25", "amount": 3200, "category": "식비"}
print(receipt["store"])
receipt["memo"] = "야식"   # 새 항목 추가
print(receipt)

# 5) if
if amount >= 10000:
    print("큰 금액")
elif amount >= 3000:
    print("보통 금액")
else:
    print("작은 금액")

# 6) for: 리스트를 하나씩 꺼낸다.
receipts = [
    {"store": "GS25", "amount": 3200, "category": "식비"},
    {"store": "스타벅스", "amount": 5500, "category": "카페·간식"},
    {"store": "지하철", "amount": 1500, "category": "교통"},
]
total = 0
for r in receipts:
    total += r["amount"]
    print(f"- {r['store']}: {r['amount']}원")
print("총합:", total)


# 7) 함수: def 로 만들고, 들여쓰기로 몸체를 적는다.
def get_total(items):
    total = 0
    for item in items:
        total += item["amount"]
    return total


def get_by_category(items, category):
    result = []
    for item in items:
        if item["category"] == category:
            result.append(item)
    return result


print("총합:", get_total(receipts))
print("카페·간식:", get_by_category(receipts, "카페·간식"))

# 과제
# 1. 카테고리별 합계를 구하는 함수 get_category_total(items, category) 를 만들어 보세요.
# 2. 금액이 가장 큰 영수증을 찾는 함수 get_max_receipt(items) 를 만들어 보세요.
# 3. 가게 이름 목록만 뽑아 리스트로 돌려주는 함수를 만들어 보세요.
