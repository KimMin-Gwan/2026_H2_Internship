// ocrEngine.ts 단위 테스트 — npm test (node --test)

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ocrEngineLabel } from './ocrEngine.ts';

test('ocrEngineLabel: 실제 분석은 모델 이름, mock 은 예시 결과, 모르면 빈 문자열', () => {
  assert.equal(ocrEngineLabel('claude', 'claude-haiku-5-5'), 'claude-haiku-5-5');
  assert.equal(ocrEngineLabel('openai', 'gpt-6-luna'), 'gpt-6-luna');
  assert.equal(ocrEngineLabel('mock', ''), '예시 결과');
  assert.equal(ocrEngineLabel('', ''), '');
});
