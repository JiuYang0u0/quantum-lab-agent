# Quantum Lab Agent：本地交付說明

## 完成範圍

- A0/A1：OpenAI-compatible provider、B HTTP QEC工具、有界Agent、SQLite trace、固定數值報告、明確單報告完成策略。
- A2：2–6 qubits、最多64 gates，Bell/GHZ獨立目標、理想驗證、density-matrix噪聲模擬、counts、資源與图檔。
- A3：繁體中文Web、明確工具家族、工具耗時、歷史、JSON/Markdown匯出、受限artifact圖檔。
- 指定NVIDIA CLI及正式原生Web案例已保存；原始失敗／成功證據與版本化評估器分開，沒有覆寫歷史失敗。

## 架構

```text
Browser :5174 → A FastAPI :8100 → bounded Agent → configured LLM endpoint
                                      ├ quantum → local Qiskit/Aer artifacts
                                      └ qec → B HTTP :8000 → jobs/models/reports
```

模型不取得shell工具；數值由工具結果renderer產生，模型文字另行標示。固定案例的scientific assessment與runtime completed狀態不同；completed不代表自然語言所有目標都已驗證。

## 啟動與關閉

正式原生模式依README在兩個終端啟動API與Vite，API讀取本機`.env`，前端不接觸key。QEC另啟動B；Quantum不需要B。第一次安裝用`uv sync --locked`及前端`npm ci`。

原生服務：在各自啟動終端按Ctrl+C。關閉瀏覽器不取消Agent；A停止也不保證取消已提交的B job或正在執行的CPU計算。依trace的job ID另查B。

Docker：`docker compose up --build -d`，停止用`docker compose down`，不要加`-v`除非確定要刪資料。A Compose不管理B；容器B URL與主機URL須依README設定。

Docker config與image build已驗證；尚未把正式容器中的NVIDIA推論當成已通過端到端測試。真實Web證據來自原生API/Vite。

## 零外部API測試

```powershell
uv run pytest -q
uv run ruff check .
uv build
uv run python docs/evidence/a3-nvidia-web-20261009/verify.py
```

```powershell
cd frontend
npm ci
npm test
npm run build
```

上述pytest與verifier不呼叫真實模型。`doctor --probe-tools`、`run`及live eval scripts則可能消耗設定provider額度；需明確設定步數、工具與時間预算。

## 驗收摘要

最近完整Python驗證235tests通過；frontend6tests與build已通過。保存的NVIDIA正式Web兩案共7completion：Bell4次43.222秒、QEC3次43.904秒。Bell fidelity1；QEC32test shots之MWPM0、lookup0、MLP3 failures。這是smoke，不是解碼器優勢或多案例可靠性估計。

Bell額外analyze工具不符合原固定四工具鏈；原strict failure保留，scoped science與五工具綁定另行驗證。QEC使用v2 native→execution→job→artifact gate。原始HTTP wire URLs未保存，不宣稱wire-level endpoint取證。

## 資料與發布界線

`.env`、`.qla/`、虛擬環境、build outputs預設不進Git。已精選的`docs/evidence`是經遮蔽的實驗素材，但可能仍有本機路徑、run/artifact IDs與prompt；對外發布前按分享範圍再審查，不將本地收尾等同公開授權。

正式Web資料預設`.qla/workbench`；fixture使用獨立root且有mode標記，不能混用。保留SQLite與其引用的科學artifacts，僅複製報告不保證能再次驗證全部來源。

## 未完成或不在範圍

- QPU/GPU實測、正式Docker NVIDIA推論、多人授權／公網部署。
- 任意電路／noise模型、live模型錯誤修正、系統性多案例可靠性研究。
- RAG、多Agent、自由形式數值解讀、正式PPTX。
- Git遠端發布、PR／main整合另待使用者決定。

## 展示順序（約3分鐘）

1. 選Quantum，說明Bell目標與ideal/noisy fidelity的區別。
2. 展示工具參數、耗時、artifact圖與固定數值報告。
3. 切QEC，說明B工作流、資料集／checkpoint來源與report_ready。
4. 匯出歷史報告，說明哪些是fixture、哪些是真NVIDIA證據，以及未測項目。
