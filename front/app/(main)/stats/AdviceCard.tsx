'use client';

// N1 AI 소비 분석 카드 — 버튼을 누르면 그 달의 소비 데이터를 AI가 분석해 요약과 조언을 문장으로 보여 준다.
// 결과는 저장하지 않으므로 화면을 떠나면 사라진다 (02 문서 5절, 시안 N1·N1b)

import { useState } from 'react';
import { RefreshCw, Sparkles } from 'lucide-react';
import { useToast } from '../../_components/Toast';
import { analyzeSpending, errorText, type SpendingAdvice } from '../../_lib/api';
import { ocrEngineLabel } from '../../_lib/ocrEngine';
import s from './stats.module.css';

export function AdviceCard({ month }: { month: string }) {
  const showToast = useToast();
  const [advice, setAdvice] = useState<SpendingAdvice | null>(null); // null = 아직 분석하지 않음
  const [loading, setLoading] = useState(false);

  async function analyze() {
    setLoading(true);
    try {
      setAdvice(await analyzeSpending(month));
    } catch (err) {
      showToast(errorText(err));
    } finally {
      setLoading(false);
    }
  }

  if (!advice) {
    return (
      <section className={`${s.advice} ${s.adviceIdle}`}>
        <span className={s.aiIcon}><Sparkles size={20} aria-hidden="true" /></span>
        <div className={s.adviceText}>
          <h2 className={s.adviceTitle}>AI 소비 분석</h2>
          <p className={s.adviceSub}>이번 달 소비 패턴과 조언</p>
        </div>
        <button type="button" className={s.adviceButton} disabled={loading} aria-busy={loading} onClick={analyze}>
          {loading ? '분석 중' : '분석'}
        </button>
      </section>
    );
  }

  const engine = ocrEngineLabel(advice.ai_provider, advice.ai_model); // 이 글을 쓴 AI
  return (
    <section className={`${s.advice} ${s.adviceResult}`}>
      <div className={s.adviceHead}>
        <span className={`${s.aiIcon} ${s.aiIconSmall}`}><Sparkles size={16} aria-hidden="true" /></span>
        <h2 className={s.adviceTitle}>AI 소비 분석</h2>
        {engine && (
          <span className={s.engine} aria-label={`분석 AI ${engine}`}>
            <Sparkles size={13} aria-hidden="true" />
            <span className={s.ellipsis}>{engine}</span>
          </span>
        )}
      </div>
      <p className={s.summary}>{advice.summary}</p>
      <ol className={s.adviceList}>
        {advice.advices.map((text, index) => (
          <li key={index} className={s.adviceItem}>
            <span className={s.number} aria-hidden="true">{index + 1}</span>
            <span>{text}</span>
          </li>
        ))}
      </ol>
      <button type="button" className={s.again} disabled={loading} aria-busy={loading} onClick={analyze}>
        <RefreshCw size={14} aria-hidden="true" className={loading ? s.spin : undefined} />
        {loading ? '분석 중' : '다시 분석'}
      </button>
    </section>
  );
}
