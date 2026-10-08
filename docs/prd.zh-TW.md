# Quantum Lab Agent — 產品需求文件（PRD）

| 欄位 | 內容 |
|---|---|
| 文件版本 | 1.0 |
| 對應產品 | 0.1.0，本地已實作／尚未發布 |
| 文件日期 | 2026-10-09 |
| 維護者 | JiuYang |
| 文件性質 | 依既有實作與驗收證據整理的現況 PRD，不是尚未實作的承諾 |
| 授權 | Apache-2.0；第三方依賴各自保留授權 |

## 1. 產品摘要

Quantum Lab Agent 是以自然語言操作量子實驗的**本機單人研究與學習工作台**。使用者透過 CLI 或繁體中文 Web 提出任務，由古典 LLM 選擇受限工具，執行本地量子電路模擬或外部 QEC 管線，再取得附設定、來源 ID 與執行紀錄的數值報告。

**核心價值：降低實驗操作門檻，同時保留結果的可驗證性。**

LLM 負責規劃；Qiskit/Aer 或 QEC 工具負責計算；固定 renderer 負責數值報告。它不是量子 LLM，不在 QPU 上訓練或執行語言模型，也不保證模型能解決任意研究問題。

## 2. 問題與機會

### 2.1 使用者面臨的問題

1. 從理論走到實驗，需要理解多個 SDK、參數與結果格式。
2. 取樣、訓練、等待、比較與紀錄涉及多步操作，容易傳錯 artifact 或混用配置。
3. 一般聊天模型可能生成看似合理但沒有實驗依據的數字。
4. 只有最終圖表，往往無法追溯模型、電路、噪聲、shots、seed 或資料來源。
5. 模型說「完成」、程式成功執行、科學目標成立，是不同層次，容易被混淆。

### 2.2 產品策略

以兩個邊界清楚的工具家族提供可執行流程；使用 schema、預算、獨立科學驗證與來源鏈約束工具。將模型文字與數值證據分開，使成功與失敗都可檢視、匯出及重播。

本產品補足既有 SDK 的操作與紀錄層，不取代 SDK、論文判讀或研究者的科學判斷。

## 3. 使用者與使用情境

| 角色 | 先備條件 | 主要需求 |
|---|---|---|
| 主要：量子／Agent 學習者 | 基本 Python、終端機與量子概念 | 把自然語言任務連到真實工具，理解每一步與結果 |
| 次要：AI 工程開發者 | API、工具呼叫與測試經驗 | 研究長任務、工具參數、失敗處理與可追溯報告 |
| 延伸：研究原型開發者 | 能判斷噪聲與統計假設 | 快速執行有界範例、比較解碼器並保留證據 |

### 使用者故事

- **US-01**：身為學習者，我希望建立 Bell 態並驗證結果，知道「counts 看起來對」和「狀態正確」的差別。
- **US-02**：我希望分別加入閘噪聲與讀取錯誤，觀察量測前 fidelity 與 counts 如何改變。
- **US-03**：我希望用同一測試集比較 MLP 與 MWPM，並知道模型、資料與報告的來源。
- **US-04**：我希望看到 Agent 實際呼叫哪些工具、花多少時間、哪一步失敗，而不是只收到一句結論。
- **US-05**：我希望沒有 API key 時也能試用介面，但能清楚知道那是 fixture。
- **US-06**：我希望之後重新打開歷史紀錄與匯出報告，不必再消耗模型額度。

## 4. 目標、非目標與產品邊界

### 4.1 0.1.0 目標

- 提供可使用的 Quantum 與 QEC 兩種流程，模式由使用者明確選擇。
- 對執行設定、工具輸入、時間與呼叫數設立明確邊界。
- 報告中的數值有實際工具與 artifact 來源。
- 提供 CLI、Web、持久化紀錄及離線重播。
- 以本地模擬、確定性測試與指定真實 LLM 案例驗收。
- 陌生開發者可依公開文件安裝、試用與執行離線測試，不依賴私人 KB。

### 4.2 非目標

- 任意 Python、shell 或不受限電路執行。
- 已驗證的 QPU/GPU 實驗、量子加速 LLM。
- 多人帳號、公網部署、跨使用者權限系統。
- RAG、多 Agent 協作或任意研究問題自動解決。
- 保證神經解碼器優於 MWPM，或保證所有自然語言任務成功。
- 自動取消所有外部 B 工作／已啟動的 CPU 計算。

## 5. 核心產品流程

```text
使用者（CLI / Web）
  → 明確選擇 family 與預算
  → Agent 呼叫已設定的 LLM
  → schema 驗證工具參數
  → Quantum 本地工具 / QEC 外部 HTTP 工作
  → 結果與來源驗證
  → 固定數值報告 + 分開標示的模型文字
  → 歷史 / 匯出 / 離線重播
```

### 5.1 首次體驗

1. 安装鎖定依賴。
2. 先使用 fixture 工作台，確認模式選擇、事件、報告與圖表可用。
3. 切換正式服務，設定 provider、精確 model ID 與本機金鑰。
4. Quantum 不需要 B；QEC 必須另啟動相容的 B API。
5. 在明確步數／工具／時間預算內提交小型任務。

Fixture 不理解任意需求：固定假模型＋本地真 Aer／QEC mock，頁面與匯出皆須標示，不列入真 Agent 成功證據。

### 5.2 Quantum 流程

範例：「建立 Bell 態、驗證，使用 1024 shots、seed 7 模擬並讀取報告。」

`build_circuit → verify → run_simulation → quantum_read_report`；依需求另用 `analyze` 或 `plot`。

允許 2–6 qubits、最多 64 gates 的受限電路。Bell/GHZ 目標獨立定義；fidelity 由量測前狀態／密度矩陣計算，不從 counts 推論。資源分析報告 transpilation basis、seed、optimization 與 all-to-all 假設，不當成真實 QPU 成本。

理想建構不符時回傳 `target_mismatch`，修正流程最多三次且目標固定；合法電路加入噪聲後 fidelity 下降，不當成建構失敗。既有錯誤 circuit 的模擬或讀報告不能繞過此判定。

### 5.3 QEC 流程

範例：「生成小型重複碼資料、訓練一個 MLP，與 MWPM 比較並交付一份報告。」

`qec_sample → qec_train → qec_compare`；另有 `qec_list_artifacts`、`qec_read_report`。

Runtime 管理 B 的 job 輪詢，不為每次輪詢額外呼叫 LLM。模型傳遞 dataset/checkpoint IDs；比較結果保留 errors/shots、LER、CI 與來源。單報告任務可明確選擇報告目標 1，達成後以 `report_ready` 結束，省去模型重抄數字。

### 5.4 歷史、失敗與恢復

- 保留 request/run ID、事件與 grounded output，可匯出 JSON/Markdown。
- Web 同一 request ID＋相同原始內容可確認原提交；不同內容回傳 409。
- B POST 結果不明時不自動重送；需依 job 記錄人工確認。
- 瀏覽器關閉不停止背景 run；服務重啟將未完成 run 標為 `interrupted`，不默默重新提交。
- Replay 只呈現保存證據，不重新呼叫模型或重跑實驗。

## 6. 功能需求與驗收

P0 為本版本必要需求；P1 為本版本已交付的輔助功能。所有「已實作」均限下列邊界。

| ID | 等級 | 需求與驗收條件 | 狀態 |
|---|---|---|---|
| FR-01 | P0 | 明確選擇 quantum/qec；工具集合依 family 固定，模型不可切換 | 已實作 |
| FR-02 | P0 | Provider 使用精確配置 model；設定與使用量可追蹤，不偷偷 fallback | 已實作；指定模型案例已測 |
| FR-03 | P0 | 工具 schema 拒絕未知欄位、非法型別／索引及超額參數 | 已實作＋回歸測試 |
| FR-04 | P0 | 有模型步數、工具次數與 wall-time 上限；失敗工具也計入预算 | 已實作 |
| FR-05 | P0 | Quantum 建構、驗證、模擬、分析、繪圖、報告；正確區分ideal與noisy指標 | 已實作＋本地科學驗證 |
| FR-06 | P0 | QEC 透過B完成取樣、訓練、共同比較、讀取報告 | 已實作＋指定live案例 |
| FR-07 | P0 | 數值固定renderer與模型文字分開；沒有工具證據就不宣稱實驗成功 | 已實作 |
| FR-08 | P0 | 比較報告綁定要求的dataset/checkpoints與decoder列，重讀不得繞過限制 | 已實作＋竄改反例測試 |
| FR-09 | P0 | 持久化Web request digest，同ID不同內容409，遮蔽不改變身份判定 | 已實作 |
| FR-10 | P0 | API key僅後端持有；trace遮蔽密鑰、不保存reasoning文字 | 已實作＋測試 |
| FR-11 | P0 | 圖檔須屬該run、路徑受限、hash正確，拒絕linked/junction祖先 | 已實作＋測試 |
| FR-12 | P1 | 工具卡顯示參數、結果、錯誤與elapsed；未確認結束不虛構duration | 已實作＋瀏覽器驗收 |
| FR-13 | P1 | 歷史、JSON/Markdown匯出與離線replay；重啟保留完成資料 | 已實作 |
| FR-14 | P1 | 明確fixture入口，不能從production request切換；資料root不得混用 | 已實作 |
| FR-15 | P1 | QEC可宣告N份不同報告；重讀不重複計數，一般多步模式仍保留 | 已實作；不適用quantum |
| FR-16 | P1 | 可選CLI解讀有獨立预算，只選已審核非數值概念提醒 | 已實作；非自由研究解讀 |

詳細欄位、工具清單与routes以[工具參考](tool-reference.md)、[API參考](api-reference.md)與實際schemas為準。

## 7. 非功能需求

| 面向 | 要求及界線 |
|---|---|
| 運行環境 | Python 3.12驗證基線；前端Node.js 22.12+；單API worker／單instance／每個root單一active Agent |
| 可觀測性 | 保留工具與模型事件、finish reason、數值usage、run/job/artifact IDs；不保存推理正文 |
| 可重現性 | 鎖檔、模型配置、版本、seed與原始結果；不保證跨環境逐位元一致或live模型完全重現 |
| 資料完整性 | 以hash与schema驗證artifacts及來源鏈；hash是完整性檢查，不是第三方簽章或遠端執行認證 |
| 資源控制 | 有界qubits/gates/shots與Agent預算；await逾時不保證終止已啟動的CPU執行緒或B job |
| 使用體驗 | 繁體中文、窄螢幕可用、狀態／錯誤可讀；已做自動a11y檢查，不宣稱正式認證 |
| 資料保存 | `.qla`保存trace/artifacts；由使用者管理生命週期，無自動資料保留SLA |
| 部署 | loopback本機；Docker檔案已建置檢查，但正式容器NVIDIA端到端尚未驗證 |

不訂未經量測的吞吐量、可用性或固定回覆延遲 SLA。單一任務耗時同時受模型、網路、工具與機器影響。

## 8. 狀態語意與驗證層次

| 狀態／結果 | 意義 |
|---|---|
| `completed` | runtime觀察模型停止；不保證任意自然語言科學目標已成立 |
| `report_ready` | QEC明確宣告的報告目標已通過驗證，由policy停止，不假稱模型stop |
| `target_mismatch` | 相關電路未達固定理想目標驗證條件 |
| `time_budget` / `step_budget` | 使用完相應預算，需查看已產生的部分證據 |
| `interrupted` | Web服務重啟／關閉等導致未完成工作，沒有自動resume |
| offline `task_success` | 評估器核對特定案例契約的結果，與runtime停止原因分開 |

科學工具測試、固定假模型測試、真LLM案例、Web端到端，是四種不同證據。任何一種都不能替代其他三種。

## 9. 成功指標與目前證據

### 9.1 已量測

| 指標／案例 | 保存結果 | 能支持的結論 |
|---|---|---|
| 離線回歸 | 235項Python、6項frontend測試通過；lint/build通過 | 已覆蓋合約與回歸案例，不是全域正確性證明 |
| Bell ideal | fidelity1；1024shots，00=527、11=497 | 指定電路及模擬設定符合已知目標 |
| GHZ3 gate noise | fidelity0.926984；1q=.02、2q=.04、readout0 | 指定噪聲模型，非硬體校準預測 |
| NVIDIA正式Web Bell | 4completion／5tools，43.222秒 | 此瀏覽器任務成功完成並有科學結果 |
| NVIDIA正式Web QEC | 3completion／3tools，43.904秒，report_ready | 此QEC來源鏈與報告目标通過 |
| QEC32shot smoke | MWPM0/32、lookup0/32、MLP3/32 | 管線可執行；樣本不足以宣稱解碼器優勢 |

證據：[結果總覽](results.md)、[公開證據索引](evidence/README.md)、[Web驗收](evidence/a3-nvidia-web-20261009/README.md)。

Bell Web因增加資源分析而有第五個工具，舊四工具嚴格驗收的失敗保留；新的scoped驗證另外檢查完整呼叫／結果綁定。Gemma的歷史參數錯誤、timeout、token截斷與成功案例同樣保留，不能只展示成功。

### 9.2 尚未建立的產品指標

首次成功時間、使用者滿意度、跨案例成功率、平均成本、P95延遲、長期使用留存均未系統量測。後續需先固定任務集、模型版本、预算及重複次數，才提出數值目標；目前不編造達成率。

單次NVIDIA與Gemma時間不能當成受控benchmark，因模型、硬體、cache、token预算與收尾策略不同。

## 10. 依賴與整合

- LLM：OpenAI-compatible HTTP；需逐provider/model驗證native tools，不保證所有相容端點皆可用。
- Quantum：Qiskit/Aer本地CPU，QPU與IBM帳號不在必要路徑。
- QEC：獨立B API提供jobs/artifacts/results；A不import B Python，也不管理其服務生命週期。
- UI/API：React/Vite＋FastAPI，SQLite與本地artifacts。
- 路徑：Web5174、A API8100；B預設8000，可由後端設定。容器中的localhost不是主機。

參見[架構](architecture.md)、[設定](configuration.md)、[專案結構](project-structure.md)。

## 11. 發布與驗收標準

### 本地0.1.0交付

- 核心功能、CLI/Web與文檔符合上述P0需求。
- 完整離線測試、frontend build、套件build與保存證據verifier通過。
- fixture與正式模式明確區分，模型與科學成功範圍如實標記。
- LICENSE、貢獻文件、issue/PR templates與CI配置存在。
- 原始證據不為使驗收通過而改寫；新版評估器與歷史summary版本分開。

### 尚未發生的發布動作

本文件對應**unreleased本地版本**。遠端public repo、GitHub CI實際執行、正式release/tag、套件發布均需後續執行與驗證；存在workflow檔案不等於CI已通過。Linux runtime尚未完成實測。

## 12. 風險與對策

| 風險 | 目前對策 | 殘餘限制 |
|---|---|---|
| 模型錯誤參數／提早停止 | 嚴格schema、工具錯誤、預算、保存失敗trace | 不保證模型自行修復 |
| 生成無依據數值 | 固定renderer、來源ID、模型文字分離 | 自由文字並非全面事實驗證 |
| 重複提交昂貴工作 | request digest與B durable intent | 新run仍可能建立新實驗；無跨系統exactly-once |
| 工具結果／artifact被替換 | hashes、schema、ID來源綁定 | 非簽章，不抵抗任意有權改寫整個store的對手 |
| 逾時與程序中斷 | 保留部分證據、interrupted、bounded shutdown | 不保證取消外部jobs／CPU threads |
| 小樣本被誤認研究結論 | K/N、CI與smoke標示 | 使用者仍需掌握統計假設 |
| 文件／provider規格變動 | 鎖檔、精確model ID與版本化驗收 | 遠端模型行為仍可能改變 |

## 13. 後續規劃（未承諾時程）

1. 完成發布素材分享檢查、遠端與CI實際驗證。
2. 建立預先指定、多案例、多次重複的provider評估。
3. 擴充宣告式任務目标與有來源的解讀能力。
4. 若有需求，再評估正式容器live流程、其他電路／噪聲模型。

QPU、多人服務與大型研究演算法需另立需求，不作為0.1.0隱含承諾。完整候選項目見[Roadmap](roadmap.md)。

## 14. 產品展示建議

三分鐘展示：先說明「模型規劃、工具計算、證據報告」→Quantum Bell與噪聲差異→QEC共同測試比較→工具耗時與歷史匯出→最後交代fixture/live、smoke/benchmark及未測範圍。

本PRD維護產品目的與驗收範圍；操作旗標與API欄位以[入門](getting-started.md)、[工具參考](tool-reference.md)、[API參考](api-reference.md)為準，避免在多份文件維護不一致的指令。
