# 소비 조언 실패 — code 는 API의 error_code 와 같다 (advice_failed, advice_timeout).


class AdviceError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def advice_failed() -> AdviceError:
    return AdviceError("advice_failed", "분석하지 못했습니다")


def advice_timeout() -> AdviceError:
    return AdviceError("advice_timeout", "분석 시간이 초과되었습니다")
