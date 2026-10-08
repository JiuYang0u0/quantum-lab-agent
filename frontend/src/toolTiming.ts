import { active, type Event, type Run } from './types'

// Native Agent executes tools sequentially. Never match by name across another
// call/terminal boundary, or attach an orphan result to a previous invocation.
export function toolTimings(run: Run, now: number): Map<number, string> {
  const labels = new Map<number, string>()
  let pending: Event | undefined
  const incomplete = () => {
    if (pending) labels.set(pending.seq, `${run.status === 'time_budget' ? '逾時' : '未完成'} · 未收到結束事件，耗時未確認`)
    pending = undefined
  }
  for (const event of [...run.events].sort((a,b)=>a.seq-b.seq)) {
    if (event.kind === 'tool_call') {
      incomplete()
      pending = event
    } else if (['tool_result','tool_error'].includes(event.kind)) {
      if (pending && pending.data.tool === event.data.tool) {
        const elapsed = event.created - pending.created
        labels.set(pending.seq, elapsed >= 0 && Number.isFinite(elapsed)
          ? `${event.kind === 'tool_error' ? '失敗' : '已完成'} · 耗時 ${elapsed.toFixed(2)} 秒`
          : '時間戳異常 · 耗時未確認')
        pending = undefined
      } else incomplete()
    } else if (['finish','server_error'].includes(event.kind)) incomplete()
  }
  if (pending) {
    if (active(run.status)) labels.set(pending.seq, `執行中 · 已經過 ${Math.max(0,now-pending.created).toFixed(2)} 秒`)
    else incomplete()
  }
  return labels
}
