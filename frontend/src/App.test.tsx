import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import App from './App'
import { Evidence, Tools } from './Evidence'
import type { Run } from './types'
import { toolTimings } from './toolTiming'

beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })
const config = { profile: 'offline-fixture', model: 'exact/model', max_tokens: 512, fixture: true,
  defaults: { max_steps: 6, max_tools: 5, seconds: 120 }, bounds: {max_steps:30,max_tools:30,seconds:1800} }

test('shows server settings and mock banner; explicit family; no automatic POST retry', async () => {
  const requests: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?: RequestInit) => {
    requests.push(options?.method || 'GET')
    if (options?.method === 'POST') throw new Error('connection lost')
    return { ok: true, json: async () => url === '/api/config' ? config : [] }
  }))
  render(<App />)
  expect(await screen.findByText(/exact\/model/)).toBeInTheDocument()
  expect(screen.getByText(/離線測試模式/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('實驗需求'), {target: {value: 'Bell'}})
  expect(screen.getByRole('button', { name: '開始實驗' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('工具家族'), {target: {value: 'quantum'}})
  expect(screen.getByLabelText('QEC 報告目標')).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: '開始實驗' }))
  await screen.findByText(/提交結果不明/)
  expect(requests.filter(x => x === 'POST')).toHaveLength(1)
  expect(localStorage.getItem('qla.pending')).toContain('Bell')
})

test('restores run; separates model text from grounded report and tool errors', async () => {
  localStorage.setItem('qla.run', 'abc')
  vi.stubGlobal('fetch', vi.fn(async (url: string) => ({ok:true,json:async()=>
    url === '/api/config' ? config : url === '/api/runs' ? [] : {
      run_id:'abc',family:'qec',prompt:'test prompt',status:'completed_with_errors',
      grounded_output:'verified report only',events:[
        {seq:1,created:1,kind:'model',data:{content:'unverified model text'}},
        {seq:2,created:2,kind:'tool_call',data:{tool:'qec_train',args:{dataset_id:'x'}}},
        {seq:3,created:3,kind:'tool_error',data:{tool:'qec_train',error:'failed'}}]}
  })))
  render(<App />)
  await waitFor(() => expect(screen.getByText('verified report only')).toBeInTheDocument())
  expect(screen.getByText('unverified model text')).toBeInTheDocument()
  expect(screen.getByText(/模型文字（未驗證）/)).toBeInTheDocument()
  expect(screen.getByText(/failed/)).toBeInTheDocument()
  expect(screen.getByRole('link',{name:'JSON'})).toHaveAttribute('href','/api/runs/abc/export.json')
})

test('quantum evidence displays fidelity independently of counts and authorized image route', () => {
  render(<Evidence run={{run_id:'abc',family:'quantum',created:0,prompt:'',status:'completed',grounded_output:'grounded',events:[
    {seq:1,created:0,kind:'tool_result',data:{result:{kind:'quantum_simulation',artifact_id:'sim',
      premeasurement_fidelity:.75,config:{shots:128},resources:{depth:3,two_qubit_gates:1},
      verification:{status:'verified'},counts:{'00':64,'11':64}}}},
    {seq:2,created:0,kind:'tool_result',data:{result:{kind:'quantum_plots',artifact_id:'plots',
      graphics:{circuit_svg:{file:'hash.svg'}}}}}
  ]}} />)
  expect(screen.getByText('0.75000000')).toBeInTheDocument()
  expect(screen.getByText(/不由 counts 推論/)).toBeInTheDocument()
  expect(screen.getByAltText('量子電路圖')).toHaveAttribute('src','/api/runs/abc/graphics/hash.svg')
  expect(screen.getByRole('group',{name:'量測 counts'})).toBeInTheDocument()
})

const timingRun = (status:string):Run => ({run_id:'a',family:'qec',created:0,prompt:'',status,grounded_output:'',events:[
  {seq:1,created:100,kind:'tool_call',data:{tool:'qec_train',args:{}}},
  {seq:2,created:102,kind:'tool_result',data:{tool:'qec_train',result:{}}},
  {seq:3,created:103,kind:'tool_call',data:{tool:'qec_train',args:{}}},
  {seq:4,created:106,kind:'tool_error',data:{tool:'qec_train',error:'failure'}},
  {seq:5,created:107,kind:'tool_call',data:{tool:'qec_train',args:{}}}
]})

test('sequential repeated tool names have separate durations and a live elapsed timer', () => {
  vi.useFakeTimers();vi.setSystemTime(110000)
  try {
    render(<Tools run={timingRun('running')}/> )
    expect(screen.getByText('已完成 · 耗時 2.00 秒')).toBeInTheDocument()
    expect(screen.getByText('失敗 · 耗時 3.00 秒')).toBeInTheDocument()
    expect(screen.getByText('執行中 · 已經過 3.00 秒')).toBeInTheDocument()
    act(()=>vi.advanceTimersByTime(1000))
    expect(screen.getByText('執行中 · 已經過 4.00 秒')).toBeInTheDocument()
  } finally {vi.useRealTimers()}
})

test('missing result never pairs an older repeated-name call across another call', () => {
  const run=timingRun('completed')
  run.events=run.events.filter(e=>e.seq!==2)
  const labels=toolTimings(run,110)
  expect(labels.get(1)).toContain('未完成')
  expect(labels.get(3)).toBe('失敗 · 耗時 3.00 秒')
  expect(labels.get(5)).toContain('未完成')
})

test('timeout and interrupted tools have no invented completed duration', () => {
  const {rerender}=render(<Tools run={timingRun('time_budget')}/> )
  expect(screen.getByText('逾時 · 未收到結束事件，耗時未確認')).toBeInTheDocument()
  rerender(<Tools run={timingRun('interrupted')}/> )
  expect(screen.getByText('未完成 · 未收到結束事件，耗時未確認')).toBeInTheDocument()
  expect(screen.queryByText(/執行中 · 已經過/)).not.toBeInTheDocument()
})
