// 영수증 분석에 쓴 AI를 화면에 보여 줄 이름으로 바꾼다 (O3 인식 결과, S1 설정)

// provider: mock | openai | claude. mock 은 실제 분석이 아니므로 모델 이름 대신 "예시 결과"로 보여 준다.
// 알 수 없으면(이 정보가 생기기 전의 영수증 등) 빈 문자열을 돌려주고, 화면은 표시하지 않는다.
export function ocrEngineLabel(provider: string, model: string): string {
  if (provider === 'mock') return '예시 결과';
  return model || '';
}
