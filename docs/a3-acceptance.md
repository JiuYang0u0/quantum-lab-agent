# A3 本地離線 Web 驗收

已驗證版本：`4ebd84d`。本頁是離線 fixture 驗收，不是 NVIDIA Web 執行證據。

## 證據

- Python 全套193 tests通過；frontend6 tests通過；Ruff、TypeScript/Vite build、wheel/sdist建置通過。
- 獨立review關閉request digest去重、父目錄junction邊界與工具elapsed三項問題；原始反例均重驗通過。
- 重啟fixture後端後，瀏覽器Quantum run `9d244b0497b44e64bcc3834e2760129a`：固定provider→真Aer Bell128shots→圖檔，completed。Fidelity1，counts00:69/11:59，電路深度4。
- 前一fixture QEC run `7a3631de26de419eb1b1ce4e064aaedc`：mock report，report_ready；JSON與Markdown匯出HTTP200，重啟後歷史仍可查。
- 兩個quantum SVG均載入成功，run授權與hash檢查在API測試覆蓋。
- 工具卡實際顯示build0.04秒、simulation0.09秒、plot2.41秒（本次觀察，非效能benchmark）。
- 行動390×844 document寬390、無頁面水平溢出；桌機1440×1000截圖已檢查。
- 最終Quantum頁面axe WCAG2A/AA：0 violations、0 incomplete；QEC行動頁面同樣0/0。自動檢查不等於正式無障礙認證。

## 限制與後續

本頁記錄的離線驗收當時尚未使用NVIDIA從Web跑真Agent。後續原生正式Web驗收見
[2026-10-09 NVIDIA production evidence](evidence/a3-nvidia-web-20261009/README.md)：
Bell與QEC科學任務通過，共7次completion。尚未啟動正式provider容器；Docker config/image build由實作者驗證，不能稱為已測正式容器端到端。
Fixture明確標示假模型/QEC mock；Quantum數值是本地真Aer。無真模型API消耗、無QPU提交。
正式Web live驗收須另行確認呼叫預算；CLI NVIDIA既有證據不替代Web測試。
