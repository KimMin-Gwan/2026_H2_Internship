'use client'

import {useState} from "react";
import s from './page.module.css'; 

export default function Home() {
  const [result, setResult] = useState('');

  const data = { store: 'GS',
                 amount: 4500,
                 category: '식비' 
                };

  async function send() {

    try {
      const res = await fetch('/api/receipt/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: { body: {data}} }), // 객체를 JSON 문자열로 바꿔서 보낸다
      });
      const json = await res.json(); // 응답 JSON을 다시 객체로 바꾼다
      console.log(json);
      setResult(JSON.stringify(json, null, 2));
    } catch {
      setResult('서버에 연결할 수 없습니다');
    }
  }

  return (
    <main className={s.main}>
      <h1 className={s.title}>JSON 보내기</h1>
      <button className={s.button} onClick={send}>보내기</button>
      {result && <pre className={s.result}>{result}</pre>}
    </main>
  );
}

