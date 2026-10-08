# Quantum Lab Agent — Project A / A3 Workbench

獨立的 Python CLI 與繁體中文 React 工作台；透過 OpenAI-compatible HTTP 與模型溝通，透過 HTTP 呼叫 Project B。無 shell/exec 工具、無 B Python import、無私有知識庫依賴。既有 CLI 指令保持相容。

## 交付導覽

本地 A0–A3 與指定 NVIDIA CLI／Web 案例已驗收。這是本機單人研究／學習工具，不是任意任務成功率或 QPU 能力保證。

| 想做的事 | 入口 |
|---|---|
| 快速了解架構、範圍與停止方式 | [交付說明](handoff.md) |
| 零 API 費用查看工作台 | 下方「完全離線驗收入口」；頁面明示 fixture |
| 使用 Bell/GHZ 與噪聲工具 | [A2 使用指南](a2-quantum.md) |
| 核對真實 NVIDIA Web 結果 | [兩案原始證據與 verifier](evidence/a3-nvidia-web-20261009/README.md) |
| 理解 QEC／quantum 評估修正 | [QEC v2](qec-assessment-v2.md)、[Quantum v2](a2-assessment-v2.md) |
| 離線測試與套件建置 | `uv run pytest -q`、`uv run ruff check .`、`uv build` |

**模式界線：** `quantum` 只需 A 的本地 Qiskit/Aer；`qec` 另需啟動 B HTTP 服務。兩者的模型規劃由設定的 LLM 提供；fixture 模式不會呼叫模型，也不能當成真實 Agent 成果。

## A3 本機工作台

**Production NVIDIA Web acceptance (2026-10-09):** Bell and QEC sample/train/compare
scientific checks passed through the real browser UI; 7 completions total under
the approved 10-call budget. Bell `completed` (4 calls), QEC `report_ready`
(3 calls). See [sanitized evidence and offline verification](evidence/a3-nvidia-web-20261009/README.md)
for numeric results, evaluator scope, screenshots, and process cleanup.

Python 3.12+、uv、Node.js 22.12+。在本 repo 根目錄執行：

```powershell
uv sync --locked
# 首次安裝才複製，勿覆寫已有的密鑰設定
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run uvicorn quantum_lab_agent.workbench:create_app --factory --host 127.0.0.1 --port 8100 --workers 1 --timeout-graceful-shutdown 5
```

另一個終端：

```powershell
cd frontend
npm ci
npm run dev
```

開啟 **http://127.0.0.1:5174**；API **http://127.0.0.1:8100**，文件 `/docs`。
A 使用 8100/5174，不佔用 B 的 8000/5173。前端只連 `/api`，Vite 代理至 8100。
`QLA_PROFILE=lmstudio`（預設）或 `nvidia`；精確模型由 `QLA_MODEL` 設定，頁首顯示伺服器實際設定。
profile 不會自動改寫已有 `.env` 的 URL/model。`QLA_API_KEY`、provider/B URL 僅在伺服器使用；瀏覽器不接收 API key、Authorization header 或 B URL。

先明確選擇 `quantum` 或 `qec`；模型不能切換工具家族。
左側輸入需求與預算，右側查看即時工具參數、結果、錯誤、時間、grounded report、QEC 表格、量子 counts／保真度／資源與已授權圖檔。
QEC 報告目標 0 表示一般模式，1–30 使用既有報告完成策略；quantum 明確拒絕此目標。
`completed` 僅代表模型停止，**不是已驗證所有研究目標**；`report_ready` 才是 QEC 宣告報告數已達成。

每個新實驗先產生固定 request ID。提交連線不明時不自動重送，使用「以相同 ID 確認提交」即可取回原 run；同 ID 不同內容會 409。
ID 綁定原始 canonical request 的 SHA-256 digest，資料庫只保存 digest 與遮蔽後 payload。升級前沒有 digest 的舊 run 仍可 GET／匯出，但再次 POST 相同 ID 會保守拒絕 409，避免無法證明原始內容相同。
工具卡以順序 trace 的 call/result/error 計算耗時；執行中顯示本機時鐘估計經過時間。逾時或中斷而沒有結束事件時標示未確認，不虛構完成耗時。
每秒輪詢、斷線自動重連；瀏覽器保留所選 run ID，歷史保留 SQLite 最近 100 筆索引，較舊 run 仍可依 ID 查詢／匯出。
同一個伺服器一次一個 Agent，必須使用 **單 worker、單實例**，不可用 reload 或共用資料根目錄多開。
預設資料根 `.qla/workbench`，可用 `QLA_WORKBENCH_ROOT` 指定；實驗、trace 與產物持久化。
重新啟動將未完成 run 標為 `interrupted`，不重新提交工具。關頁不取消實驗；伺服器關閉最多等待 worker 2 秒後標 interrupted。
沒有取消按鈕：逾時／關閉不保證取消 B job 或已在 CPU 執行的計算。worker 為 daemon；只有持續執行中的伺服器保證背景 run 繼續。
既有 QEC uncertain POST intent 規則仍適用，不重送不確定的 B POST。

### 完全離線驗收入口（禁止誤認正式成果）

先停止自己的 A API，再執行下列明確 fixture factory；不載入 `.env`、不呼叫 NVIDIA/LM Studio/B，所有 HTTP 由封閉 mock transport 接管：

```powershell
$env:QLA_FIXTURE_ROOT = '.qla/acceptance-fixture'
uv run uvicorn quantum_lab_agent.workbench_fixture:create_fixture_app --factory --host 127.0.0.1 --port 8100 --workers 1 --timeout-graceful-shutdown 5
# 前端仍用另一終端的 npm run dev，網址不變
```

頁面有「離線測試模式」橫幅；固定假模型執行 Bell → 真實本機 Aer 128 shots → circuit/histogram SVG/PNG。
QEC 使用固定 mock 報告，不是 B 計算。此入口忽略自然語言內容，只用於驗收 UI／API；正式 API 不接受 `fixture` request 欄位。
fixture 資料預設隔離在 `.qla/acceptance-fixture`，匯出帶有 fixture 標記。不要將兩種模式指到同一個資料目錄。

### API 與測試

| Method / route | 用途 |
|---|---|
| GET `/api/config` | 遮蔽後 profile、精確 model、token／request budget |
| POST `/api/runs` | `request_id`（32 hex）、`family`、`prompt`、`limits`、`reports`；202 或 409/422 |
| GET `/api/runs` | 歷史 |
| GET `/api/runs/{id}` | 狀態、完整 trace events、grounded output |
| GET `/api/runs/{id}/events?after=SEQ` | 增量重連輪詢；seq 為持久化游標 |
| GET `/api/runs/{id}/export.json` 或 `export.md` | 遮蔽後證據 |
| GET `/api/runs/{id}/graphics/{sha256}.svg` 或 `.png` | 僅限該 run 已產生且 hash 正確的核准圖檔 |

```powershell
uv run pytest -q
uv run ruff check .
uv build
cd frontend
npm test
npm run build
npm audit
```

原生 API 測試使用注入的 fake provider／MockTransport，涵蓋持久化、重連游標、預算、單一 Agent、重啟 interrupted、遮蔽、圖檔授權與 hash 損壞；quantum E2E 使用真正 Aer，無外部模型呼叫。

### 選用 Docker（A only）

```powershell
docker compose config --quiet
docker compose build
docker compose up -d
# 僅停止本專案
docker compose down
```

仍使用 localhost 8100/5174；資料在 `qla-data` volume。`.env` 只注入 API container，不進 image 或前端。
B 是獨立外部服務，預設 `http://host.docker.internal:8000`，可用 `QLA_CONTAINER_QEC_URL` 覆寫。
容器內 LM Studio 請將 `QLA_BASE_URL` 設為可達的 host 地址，例如 `http://host.docker.internal:1234/v1`。
不要同時啟動原生與容器 A。Docker 不啟動、修改或停止 B。

## 安裝與檢查（PowerShell）

```powershell
cd quantum-lab-agent
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run qla --help
uv run qla doctor
```

預設 LM Studio：`http://127.0.0.1:1234/v1`，模型 `google/gemma-4-e2b`。B 預設 `http://127.0.0.1:8000`。
`doctor` 查詢 `/models` 與 B `/api/health`；模型出現在列表**不代表支援工具**。
`doctor --probe-tools` 才會實際要求工具呼叫，最多兩次 completion、一個工具、60 秒。

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$env:QLA_QEC_URL = 'http://127.0.0.1:8000'
uv run qla doctor --probe-tools
uv run qla run --prompt '請列出現有 QEC artifacts。' --max-steps 2 --max-tools 1 --seconds 60
uv run qla run --prompt '用小型 repetition CPU 預設值 sample，train 一個 mlp，compare，然後停止。' --max-steps 5 --max-tools 3 --seconds 120
```

CLI 全域選項必須放在子命令前，例如 `qla --trace-db .qla/demo.sqlite3 run --prompt '...'`。
環境變數優先於 `.env`。密鑰只由 `QLA_API_KEY` 環境變數或本地忽略的 `.env` 載入；不寫入 provider profiles。

### NVIDIA profile

`config/providers.toml` 記錄 profile 契約；執行時由 `Settings.load()` 選擇相同預設值，並套用 `QLA_*` 環境變數（TOML 不是任意設定檔載入器）。沒有虛構 NVIDIA 模型 ID。

```powershell
$env:QLA_BASE_URL = 'https://integrate.api.nvidia.com/v1'
$env:QLA_MODEL = '<你帳戶目前可用的確切模型 ID>'
# 在目前 shell 安全設定 QLA_API_KEY；不要將真實 key 寫進命令紀錄或版本控制。
uv run qla --profile nvidia doctor
```

NVIDIA `deepseek-ai/deepseek-v4.1-flash` 已完成指定 CLI／Web live 案例，證據見上方導覽；其他模型未據此獲得驗證。若 `.env` 仍是 LM Studio 設定，須覆蓋其 URL/model，不能只切換 profile。

## 工具與執行邊界

| 工具 | B endpoint | 行為 |
|---|---|---|
| `qec_list_artifacts` | GET `/api/artifacts` | 列出資料集、checkpoint、比較報告 |
| `qec_sample` | POST `/api/jobs/sample` | 小型 CPU 取樣，等待 dataset ID |
| `qec_train` | POST `/api/jobs/train` | 既有 dataset 訓練，等待 checkpoint ID |
| `qec_compare` | POST `/api/jobs/compare` | MWPM、lookup 與選擇的 checkpoint；等待並讀取報告 |
| `qec_read_report` | GET `/api/results/{id}` | 驗證 ID 與基本數值一致性，產生引用報告 |

Pydantic 拒絕額外欄位、錯誤型別、路徑型 ID、超額 CPU 參數及重複 checkpoint。A 的取樣預設是 train/validation/test = 128/32/64，訓練 1 epoch、hidden size 8、CPU 單執行緒；實際 integration 使用 64/16/32。
A 支援 B 的簡化 noise `p`，尚未暴露四個獨立 noise override。

工作輪詢由 asyncio 執行，不交給 LLM。預設上限為 6 次模型步驟、5 次工具嘗試、120 秒；無效與失敗工具也消耗工具額度。每次模型輸出預設最多 512 tokens，可用 `QLA_MAX_TOKENS` 設定 16–2048；reasoning 模型的內部推理也會消耗此額度，因此過低值可能在可見回答或工具呼叫前截斷。整個 run 有 wall-time timeout。
agent 結束或 timeout **不會取消 B 已提交的工作**；可用 trace 的 job ID 查 B。

### 完成策略：先交付報告，解說另計

一般 `run` 預設仍由模型決定何時停止，適合多次比較、比較後還要訓練或其他後續工作的任務。
**QEC 單報告任務建議明確加上 `--finalize-on-report`**：宣告目標是取得一份已驗證報告；
收到報告立即以 deterministic renderer 交付完整數值與引用，不再呼叫模型重寫表格。
這不是從自然語言猜測任務已完成。若任務要求多份比較，指定 `--report-count N`；
以不同 comparison artifact ID 計數，重讀同一報告不重複計數。其他後續需求請使用一般模式。
單次模型回應若提出更多工具呼叫，達成宣告的報告數後不再執行剩餘呼叫。

```powershell
# 單份報告：預設不增加 finalization completion
uv run qla run --finalize-on-report --prompt '用小型 CPU 預設 sample、train mlp、compare，交付比較報告。'
# 多份報告：不能在第一份就停止；依實驗需求提高工具與時間上限
uv run qla run --finalize-on-report --report-count 2 --max-tools 10 --max-steps 12 --seconds 600 --prompt '完成兩組不同 noise 的實驗並各交付比較報告。'
# 可選概念提醒：先 flush 報告，再以獨立額度取得一個簡短句子
uv run qla run --finalize-on-report --interpret --interpretation-tokens 128 --interpretation-seconds 15 --prompt '完成一個小型 CPU QEC 比較。'
```

報告模式驗證非空結果、數值一致性與 artifact ID；`qec_compare` 另比對要求的 dataset、
checkpoint 集合與 MWPM/lookup 列覆蓋。A 不聲稱驗證自然語言中的所有研究目標。
成功狀態為 `report_ready`，`task_completion=verified_report_goal`，`termination_source=policy`；
模型提早停止但報告數不足時為 `report_goal_unmet`。一般模式的 `task_completion=unverified`
代表 runtime 沒有宣告式目標可驗證；不取代 evaluator 對固定實驗契約的 `task_success`。

`--interpret` 只適用於報告模式，預設關閉。額外至多一次 completion，預設 128 tokens / 15 秒，
可設定 16–256 tokens / 大於 0 至 60 秒；這個階段獨立於工具階段 `--seconds`，因此總上限為兩者之和。
不提供工具，也不把原始 prompt、report 或模型推理送進此階段。目前只允許模型選擇三個預先審核的
非數值概念提醒之一（smoke-test 限制、CI 意義、環境影響 timing）；任何其他文字一律拒絕發布。
這是刻意受限的可選 commentary，不是自由生成的數值分析。供應商的 `max_tokens` 可能包含 reasoning，
不能據此聲稱可獨立限制推理 tokens。`length`、timeout 或 provider 錯誤只影響 `interpretation_status`，
不抹除成功報告、不改變其數值或成功 exit code。trace 不保存被拒絕的 commentary 內容。

不加 `--interpret` 時 CLI 保持單一 JSON outcome；加上後先 flush 一個含 `event=report_ready` 的 JSON 行，
再輸出不重複 `output` 表格的 outcome JSON。程式整合若要即時取得報告，可使用 `Agent(..., on_report=callback)`。
Evaluator 對新 trace 分別提供 policy/model/budget 結束來源、真正觀測到的 `model_stop_observed`，
以及 interpretation 狀態；舊 trace 的 assessment schema 與原始證據保持相容。

### 不重複提交

SQLite 在 POST 前先記錄 client intent；同一 run、同一 B URL、同一工具及正規化參數只提交一次。收到 job ID 後重用該 job，重啟 adapter 仍有效。
網路中斷、無效回應、HTTP 拒絕或程序在 POST 後崩潰時，intent 保持 uncertain：**不重送 POST**。需要人工查看 B `/api/jobs` 後判斷。
B 沒有 server-side idempotency key，不能保證跨新 run 的全域 exactly-once；新 run 代表新實驗，可能再次提交。CLI 沒有自動 resume/重送 uncertain intent 功能。

## 數值可信度與 trace

模型純文字不會成為最終實驗答案。CLI `output` 只從實際 tool result 重建：report 用固定 renderer 讀取 `errors/shots`、LER、CI、decode seconds，每行引用 `[comparison-ID#prediction_key]`，並附 dataset ID。
B 會驗證 predictions/dataset/hash；A 再驗證 LER 與 errors/shots 一致性、有限 timing 及 ID。A 不在本地重新運算 B 的 predictions 或 Wilson CI。
無報告時顯示工具原始 JSON；沒有工具證據時顯示 `No verified tool evidence.`，即使 LLM 聲稱成功也不採信。

SQLite 預設 `.qla/trace.sqlite3`，包含實驗、模型回應、工具參數/結果、intent、job 狀態與結束原因。每次模型回應另外記錄 `finish_reason` 與數值 usage（含 reasoning token 數），不保存 `reasoning_content`。已設定 key 值、常見密鑰欄位、JSON 字串內的密鑰與 Bearer 字串會遮蔽；不記錄 HTTP headers 或伺服器錯誤 body。trace 仍可能包含 prompt 與實驗資料，請自行控管分享範圍。

```powershell
uv run qla export <RUN_ID> --output .qla/run.json
uv run qla replay .qla/run.json
uv run qla replay docs/evidence/qec-integration.json
```

Replay 是**離線證據重播**，不重新呼叫模型、不重送工作、不保證重新跑實驗產生相同 timing。JSON schema version 為 1。
CLI exit code：0 = completed 或 report_ready / doctor 模型可見（probe 時也須有工具執行）；1 = 模型未使用工具、報告目標未達成、部分工具失敗、預算用盡或 provider 問題；2 = 設定/檔案錯誤。doctor 的 B health 另外顯示，不把單純模型可見當成 QEC 可用。

## 實際測試與重跑

獨立整合腳本啟動 B 現有 `.venv` 的 uvicorn，僅讀 B source；使用 18000 port、臨時 artifact root、`PYTHONDONTWRITEBYTECODE=1`。若 port 已被使用直接失敗，不碰既有服務。不啟動 Docker。結束時清除自己啟動的 process tree，保留 temp artifact/log。

```powershell
uv run python scripts/isolated_eval.py --b-repo ../neural-qec-complete
# 以下 opt-in 最多兩次模型 completion：
uv run python scripts/isolated_eval.py --b-repo ../neural-qec-complete --with-model
# 單一 empty-args 工具 roundtrip；成功後加跑 sample-only Agent（總計最多四次）：
uv run python scripts/isolated_eval.py --b-repo ../neural-qec-complete --minimal-probe
# 一次 16-token 純文字診斷；不算 tool test：
uv run python scripts/model_diagnostic.py
```

`scripts/live_eval.py` 也可直接對已存在的 B HTTP server 執行：`uv run python scripts/live_eval.py --qec-url http://127.0.0.1:18000`。

### Autonomous multi-step evaluation

```powershell
uv run python scripts/isolated_eval.py --b-repo ../neural-qec-complete --multistep --output .qla/multistep-new-run --max-tokens 1024 --max-steps 6 --seconds 300
# opt-in 單報告完成策略；不加此 flag 則保留歷史模型停止評估流程
uv run python scripts/multistep_eval.py --output .qla/report-policy-new-run --seconds 900 --finalize-on-report
```

One native Gemma run, at most six completions/four tool attempts; no scripted tool selection,
ID injection, fallback, or retries. Output directory must be new. The model chooses sample
(64/16/32), MLP train (one epoch), and compare. Post-run assessment separately reports task
success, grounded report production, termination status, ID chain, and numeric provenance.
Offline regression fixtures cover malformed/nested arguments, ID propagation, missing
artifacts, incorrect report identity/decoder coverage, and success at the step budget.
Native tool schemas now inline nested definitions for chat-template compatibility.

離線 finalization 回歸：重播保留的 `gemma-multistep-900-trace.json` 模型訊息與工具結果，
單報告策略只使用前三次 completion；原本第四次 finalization completion 不再需要（4 → 3，少 25%）。
輸出的 deterministic report 與原 trace replay 完全相同。這是 fixture/replay 的呼叫數證據，
**不是新的 live 測試或延遲改善測量**。詳見 [finalization 離線證據](evidence/finalization-offline.md)。

**Live multi-step result: not successful.** Four total completions across two preserved
attempts: first failed nested-argument validation; after schema inlining, sample succeeded
and Gemma propagated its dataset ID into training, but the 300-second limit expired during
training. No checkpoint/comparison report was observed. See
[`docs/evidence/gemma-multistep.md`](evidence/gemma-multistep.md) for exact metadata,
failure classifications, source commits, isolation details, and original sanitized traces.

### 本次驗證結果（2026-10-07）

- Fake model/HTTP 測試與真正 B CPU integration 分開。測試涵蓋預算、無效參數、404/409/422/429/500/503、job 失敗/卡住、artifact、跨 adapter intent、不洩露 key、數值 grounding、純文字幻覺不輸出。
- **B CPU integration 通過**：sample → train → compare → read → list；MWPM、lookup、MLP 三列報告見 `docs/evidence/qec-integration.json`。
- **歷史失敗紀錄**：首次完整五工具 schema completion 90 秒 timeout、0 工具；128-token list probe 與 16-token 純文字診斷回傳空 content。當時未保留 finish_reason／usage，不能排除 token 額度不足截斷，不能以此判斷 Gemma 不支援工具；原始三次 completion 的 trace 保留不覆寫。
- **512-token follow-up 成功**：同一 `google/gemma-4-e2b`，temperature 0、native tool calling。list probe 第一次回應 `tool_calls`，執行隔離 B 的 GET artifacts 後第二次回應 `stop`；完整五工具 Agent 接著只 sample 一次，B 工作成功，第二次 completion `stop`，run 狀態 `completed`。共四次 completion，未換模型、未使用文字 JSON 偽工具 fallback。
- 新證據：`docs/evidence/lm-minimal-probe-512.json`（run `09be2ae29d9a4447ba1dae6e0d9eaf4e`）及 `docs/evidence/lm-agent-sample-512.json`（run `750da29020da40d88c4d7e156a0eea24`）。每次都有 finish_reason 與 usage；只保留 reasoning token **計數**，無推理文字。
- 四次 completion 的 `(prompt, completion, reasoning)` tokens 依序為 `(66,186,170)`、`(115,170,149)`、`(416,345,331)`、`(521,61,59)`。全功能 Agent 的 sample 第一次實際用了 345 completion tokens，說明先前 256 預算可能不足。
- 本次 B 實際 endpoint 為 `http://127.0.0.1:18000`；新 trace 的 provider_settings.qec_url 記錄環境預設 8000，probe/Agent adapter 明確覆寫為 18000。artifact 保留於當時的隔離暫存根目錄，隔離 server 已停止。sample dataset ID：`dataset-c4efaa6c857e40999ead14eb9ed63c55`。

目前包含 milestone 1、A2 local quantum 與 A3 UI：不含 RAG、任意程式執行、遠端量子硬體或跨 run 自動恢復。A3 request ID 去重不代表 B 提供 server-side 冪等性。NVIDIA A2 歷史實測見下方。
# A2 local quantum circuits

Local Bell/GHZ and restricted general gate circuits are available through
`qla quantum-tool` or the explicit Agent `run --family quantum` tool profile.
See [A2 使用說明](a2-quantum.md) and the
[offline notebook](notebooks/a2-local.ipynb).
Run `uv run python scripts/quantum_smoke.py` for actual Aer evidence and SVG/PNG artifacts.

### A2 native NVIDIA evaluation (2026-10-08)

**Both scientific tasks passed and the model stopped naturally.** Exact `.env` model:
`deepseek-ai/deepseek-v4.1-flash`, NVIDIA endpoint, `max_tokens=2048`, temperature 0.
Approved budget: two cases, at most five completions/six tools/300 seconds each,
ten completions total; actual **9 completions, 8 tools**, no retries or interpretation calls.

| Case | Completions | Seconds | Ideal target fidelity | Simulation fidelity | Task / stop |
|---|---:|---:|---:|---:|---|
| Bell ideal | 4 | 70.531 | ≈1 | 1.0 | pass / model `completed` |
| GHZ3 gate noise | 5 | 164.406 | ≈1 | 0.926984 | pass / model `completed` |

Both used 1024 shots and seed 7. GHZ3 used 1q depolarization 0.02,
2q depolarization 0.04, readout 0. Counts do not determine fidelity.
Native build → verify → simulate → read-report chains, deterministic reports,
per-completion usage/finish reasons, hashed artifacts, independent density-matrix
checks, and limitations: [live evidence](evidence/a2-nvidia-20261008.md).
This is a two-case smoke evaluation, not a reliability benchmark or QPU result.
Quantum report-count finalization remains unsupported; scientific task success is
assessed separately from the unchanged runtime termination policy.

`scripts/quantum_live_eval.py --output <new-directory>` is an opt-in **paid live**
evaluation; another execution requires a new approved budget. Offline evaluator
regressions are included in `uv run pytest -q` (148 passing at this revision).
