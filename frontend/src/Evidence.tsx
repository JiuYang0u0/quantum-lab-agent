import type { Run } from './types'
import { useEffect, useState } from 'react'
import { toolTimings } from './toolTiming'

export function Evidence({run}:{run:Run}) {
  const results = run.events.filter(e=>e.kind==='tool_result').map(e=>e.data.result)
  const reports = [...new Map(results.filter(r=>r.kind==='quantum_simulation'||r.results)
    .map(r=>[r.artifact_id,r])).values()]
  return <section className="panel evidence"><div className="section-title"><h2>已驗證工具證據</h2>
    <nav><a href={`/api/runs/${run.run_id}/export.json`} download>JSON</a> · <a href={`/api/runs/${run.run_id}/export.md`} download>Markdown</a></nav></div>
    <p className="muted">固定 renderer 數值 · 不採信模型自行撰寫的數字</p>
    {reports.map(r=><article key={r.artifact_id}>
      <h3>{r.kind==='quantum_simulation'?'量子模擬':'QEC 比較'}</h3><code className="identity">{r.artifact_id}</code>
      {r.kind==='quantum_simulation'?<>
        <div className="metrics"><div>保真度<strong>{r.premeasurement_fidelity.toPrecision(8)}</strong></div>
          <div>Shots<strong>{r.config.shots}</strong></div><div>電路深度<strong>{r.resources.depth}</strong></div>
          <div>雙量子位閘<strong>{r.resources.two_qubit_gates}</strong></div></div>
        <p>理想驗證：{r.verification.status} · 保真度由測量前密度矩陣計算，不由 counts 推論。</p>
        <div className="counts" role="group" aria-label="量測 counts">{Object.entries(r.counts).map(([label,value])=><div key={label}>
          <code>{label}</code><meter aria-label={`${label} counts`} min={0} max={r.config.shots} value={Number(value)} /> <span>{String(value)}</span></div>)}</div>
        <details><summary>資源與噪聲語意</summary><pre>{JSON.stringify({resources:r.resources,noise:r.noise_semantics},null,2)}</pre></details>
      </>:<div className="table-scroll"><table><thead><tr>{['Decoder','Errors / shots','LER','CI','秒','來源'].map(x=><th key={x}>{x}</th>)}</tr></thead>
        <tbody>{r.results.map((x:any)=><tr key={x.prediction_key}><td>{x.decoder}</td><td>{x.errors} / {x.shots}</td><td>{x.logical_error_rate}</td><td>{x.ci.join(' – ')}</td><td>{x.decode_seconds}</td><td>{r.artifact_id}#{x.prediction_key}</td></tr>)}</tbody></table></div>}
    </article>)}
    {results.filter(r=>r.kind==='quantum_plots').map(r=><div className="plots" key={r.artifact_id}>
      {['circuit_svg','histogram_svg'].map(label=>r.graphics[label]&&<figure key={label}><img alt={label==='circuit_svg'?'量子電路圖':'量測 counts 圖'} src={`/api/runs/${run.run_id}/graphics/${r.graphics[label].file}`}/><figcaption>{label==='circuit_svg'?'電路':'Counts'} · 已驗證 SHA-256</figcaption></figure>)}
    </div>)}
    <details open={!reports.length}><summary>完整 grounded report</summary><pre>{run.grounded_output}</pre></details>
  </section>
}

export function Tools({run}:{run:Run}) {
  const [now,setNow] = useState(()=>Date.now()/1000)
  useEffect(()=>{
    const timer=setInterval(()=>setNow(Date.now()/1000),1000)
    return ()=>clearInterval(timer)
  },[])
  const timings=toolTimings(run,now)
  return <section className="panel"><h2>即時工具紀錄</h2><p className="muted">參數、結果、錯誤與時間均來自 server trace</p>
    {!run.events.some(e=>e.kind==='tool_call')&&<p>等待模型規劃工具呼叫…</p>}
    {run.events.filter(e=>['tool_call','tool_result','tool_error','job','finish','server_error'].includes(e.kind)).map(e=><article className={`tool ${e.kind.includes('error')?'error':''}`} key={e.seq}>
      <div className="section-title"><strong>{e.data.tool||e.kind}</strong><time>{new Date(e.created*1000).toLocaleTimeString('zh-TW')}</time></div>
      {timings.has(e.seq)&&<p>{timings.get(e.seq)}</p>}
      <small>{e.kind}</small><details open={e.kind==='tool_call'||e.kind.includes('error')}><summary>{e.kind==='tool_result'?'查看結果':'查看詳細資料'}</summary><pre>{JSON.stringify(e.data,null,2)}</pre></details>
    </article>)}
  </section>
}
