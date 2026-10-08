import { useEffect, useState } from 'react'
import { Evidence, Tools } from './Evidence'
import { active, get, type Config, type Limits, type Run } from './types'

export default function App() {
  const [config,setConfig]=useState<Config>()
  const [family,setFamily]=useState('')
  const [prompt,setPrompt]=useState('')
  const [limits,setLimits]=useState<Limits>({max_steps:6,max_tools:5,seconds:120})
  const [reports,setReports]=useState(0)
  const [id,setId]=useState(localStorage.getItem('qla.run')||'')
  const [run,setRun]=useState<Run>()
  const [history,setHistory]=useState<Run[]>([])
  const [error,setError]=useState('')
  const [pending,setPending]=useState(localStorage.getItem('qla.pending')||'')
  const [submitting,setSubmitting]=useState(false)
  const [connection,setConnection]=useState('連線中')
  useEffect(()=>{get<Config>('/api/config').then(c=>{setConfig(c);setLimits(c.defaults)}).catch(()=>setError('無法取得伺服器設定'))},[])
  useEffect(()=>{
    let stopped=false
    let timer:ReturnType<typeof setTimeout>
    async function poll(){
      try {
        const h=await get<Run[]>('/api/runs')
        const r=id?await get<Run>(`/api/runs/${id}`):undefined
        if(!stopped){setHistory(h);setRun(r);setConnection('已連線 · 每秒同步')}
      } catch {if(!stopped)setConnection('連線中斷 · 自動重連（不重送實驗）')}
      if(!stopped)timer=setTimeout(poll,1000)
    }
    poll()
    return ()=>{stopped=true;clearTimeout(timer)}
  },[id])
  function select(identity:string){setId(identity);localStorage.setItem('qla.run',identity)}
  async function submit(){
    setSubmitting(true);setError('')
    const body=pending||JSON.stringify({request_id:crypto.randomUUID().replaceAll('-',''),family,prompt,limits,reports:family==='qec'?reports:0})
    setPending(body);localStorage.setItem('qla.pending',body)
    try {
      const response=await fetch('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body})
      if(!response.ok){
        if(response.status===409||response.status===422){setPending('');localStorage.removeItem('qla.pending');setError(`提交被拒絕（HTTP ${response.status}），請檢查預算或等待進行中實驗。`);return}
        throw new Error()
      }
      const data=await response.json();select(data.run_id);setPending('');localStorage.removeItem('qla.pending')
    }catch{setError('提交結果不明。請以相同 request ID 確認；不會自動重送或建立另一個實驗。')}
    finally{setSubmitting(false)}
  }
  return <><header><div className="brand"><span className="logo">Q</span><div><h1>Quantum Lab</h1><p>PROJECT A / 實驗工作台</p></div></div>
    <div className="provider">{config?<><strong>{config.profile} · {config.model}</strong><span>每步最多 {config.max_tokens} tokens · 單一 Agent</span></>:<span>載入伺服器設定…</span>}</div></header>
    {config?.fixture&&<div className="banner">離線測試模式：固定假模型 / QEC mock；quantum 為本機真實 Aer。不是正式模型實驗。</div>}
    <main><div className="page-title"><div><p className="eyebrow">LOCAL EXPERIMENT WORKSPACE</p><h2>從問題到可追溯的證據</h2></div><span className="connection" role="status">{connection}</span></div>
    <div className="workspace"><div className="conversation"><section className="panel"><h2>實驗對話</h2>
      <label>工具家族<select aria-label="工具家族" value={family} onChange={e=>{setFamily(e.target.value);setReports(0)}}><option value="">請明確選擇</option><option value="quantum">Quantum · 本機量子電路</option><option value="qec">QEC · B HTTP 實驗室</option></select></label>
      <label>實驗需求<textarea aria-label="實驗需求" maxLength={8000} rows={5} placeholder="例如：建立 Bell 電路，驗證、模擬並繪圖。" value={prompt} onChange={e=>setPrompt(e.target.value)}/></label>
      <div className="budget">{(['max_steps','max_tools','seconds'] as const).map((key,i)=><label key={key}>{['模型步數','工具次數','秒數上限'][i]}<input type="number" min={1} max={config?.bounds[key]||30} value={limits[key]} onChange={e=>setLimits({...limits,[key]:Number(e.target.value)})}/></label>)}</div>
      <label>QEC 報告目標<input aria-label="QEC 報告目標" type="number" min={0} max={30} disabled={family!=='qec'} value={reports} onChange={e=>setReports(Number(e.target.value))}/></label>
      <p className="muted">0 = 模型自行停止（完成未驗證）。Quantum 不支援 QEC 報告數目標。</p>
      {error&&<p role="alert" className="error">{error}</p>}
      <button disabled={submitting||!config||(!pending&&(!family||!prompt.trim()||history.some(r=>active(r.status))))} onClick={submit}>{pending?'以相同 ID 確認提交':'開始實驗'}</button>
      <p className="muted">關閉頁面不會停止工作。逾時或關閉伺服器後，B 工作與進行中的 CPU 計算可能繼續。</p>
      {run&&<div className="messages"><div className="message"><small>使用者 · {run.family}</small><p>{run.prompt}</p></div>
        {run.events.filter(e=>e.kind==='model'&&e.data.content).map(e=><div className="message model" key={e.seq}><small>模型文字（未驗證）</small><p>{e.data.content}</p></div>)}
        <p>結束／執行狀態：<strong>{run.status}</strong></p><code className="identity">{run.run_id}</code></div>}
    </section><section className="panel"><h2>實驗歷史</h2><p className="muted">最近 100 筆 · 選取後可重連、下載證據</p>{history.map(r=><button className={`history ${r.run_id===id?'selected':''}`} key={r.run_id} onClick={()=>select(r.run_id)}><strong>{r.family} · {r.status}</strong><span>{r.prompt}</span><small>{r.run_id.slice(0,12)}</small></button>)}</section></div>
    <div className="results">{run?<><Evidence run={run}/><Tools run={run}/></>:<section className="panel empty"><span>◎</span><h2>等待第一個實驗</h2><p>明確選擇工具家族，設定預算，再開始。工具紀錄與可引用的數值會出現在這裡。</p></section>}</div></div></main><footer>本機單使用者 · 數值以工具證據為準 · API 金鑰僅由伺服器持有</footer></>
}
