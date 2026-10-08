# Quantum Lab Agent

[English](README.md) · **0.1.0（尚未發布）** · [Apache-2.0](LICENSE)

本機 Python CLI 與 React 工作台，以**傳統 LLM 協調**有明確邊界的科學工具。
這不是量子 LLM。模型規劃工具呼叫，數值報告來自經驗證的工具證據。

- **Quantum：**獨立的 Qiskit/Aer CPU 模擬，支援受限 Bell/GHZ 電路、噪聲、
  目標驗證、資源分析與繪圖；不需要 QPU。
- **QEC：**透過獨立執行的外部 Project B HTTP 服務進行 sample/train/compare；
  本儲存庫不包含 B。
- **離線 fixture：**固定假模型、真正本機 Aer、模擬 QEC 報告；用於 UI/API
  驗收，不代表真實 Agent 表現。

## 快速開始：不需要模型金鑰

使用 Python **3.12**、uv，以及 Node.js **22.12+**（UI）。在儲存庫根目錄執行：

```sh
uv sync --locked
uv run python scripts/quantum_smoke.py --output .qla/quantum-smoke
uv run uvicorn quantum_lab_agent.workbench_fixture:create_fixture_app --factory --host 127.0.0.1 --port 8100 --workers 1 --timeout-graceful-shutdown 5
```

另一個終端：

```sh
cd frontend
npm ci
npm run dev
```

開啟 **http://127.0.0.1:5174**；API 文件：**http://127.0.0.1:8100/docs**。
安裝依賴需要套件來源；fixture 執行不需要模型或 B。「離線測試模式」橫幅與
固定行為是刻意設計。

真實模型模式請參考[入門](docs/getting-started.md)與[設定](docs/configuration.md)。
真實請求可能計費。每個資料根目錄只能執行單一 API instance／worker；關閉瀏覽器
不會取消實驗。

## 證據，不是效能基準

保留的 NVIDIA Web smoke 案例共使用 **7 次 completion**：Bell **43.222 秒**
（4 次），QEC **43.904 秒**（3 次），均為提交至結束時間。這些是限定範圍、各一次
的觀測，不是受控延遲比較或可靠性估計。歷史 Gemma 失敗證據仍完整保留。
Counts 不能證明量子保真度；理想驗證、含噪 density matrix 保真度與模型停止
是不同主張。詳見[結果](docs/results.md)、[限制](docs/limitations.md)與
[公開證據索引](docs/evidence/README.md)。

## 文件導覽

先了解產品定位、使用者、需求與驗收範圍：[產品需求文件（PRD）](docs/prd.zh-TW.md)。

以下整理後的參考文件以英文為主，既有繁體中文詳細指南保留。

| 開始／操作 | 理解／重現 |
|---|---|
| [入門](docs/getting-started.md) | [架構](docs/architecture.md) |
| [工作流程](docs/workflows.md) | [專案結構](docs/project-structure.md) |
| [設定](docs/configuration.md) | [可重現性](docs/reproducibility.md) |
| [工具參考](docs/tool-reference.md) | [評估](docs/evaluation.md) |
| [API 參考](docs/api-reference.md) | [結果](docs/results.md) |
| [疑難排解](docs/troubleshooting.md) | [限制](docs/limitations.md) |
| [路線圖](docs/roadmap.md) | [發布準備狀態](docs/release-readiness.md) |

[原始完整使用指南](docs/legacy-usage.md)保留作為歷史文件，相對連結已配合新位置修正。
公開副本處理方式見[來源說明](docs/public-release.md)。目前操作方式請以上方整理後指南為準。

## 開發與授權

```sh
uv run --locked pytest -q
uv run --locked ruff check .
uv build
uv run --locked python docs/evidence/a3-nvidia-web-20261009/verify.py
```

在 `frontend` 執行 `npm test` 與 `npm run build`。檢查使用離線 fixture 與本機
模擬，不呼叫付費模型。Hosted CI 已撰寫，尚未在 GitHub 執行。
參見[貢獻指南](CONTRIBUTING.md)、[安全回報](SECURITY.md)、
[行為準則](CODE_OF_CONDUCT.md)、[變更紀錄](CHANGELOG.md)與
[引用資料](CITATION.cff)。

Copyright 2026 JiuYang。採用 [Apache License 2.0](LICENSE)。第三方依賴保留各自授權。
公開試驗儲存庫：https://github.com/JiuYang0u0/quantum-lab-agent 。尚未發布正式tag版本或套件到registry。
