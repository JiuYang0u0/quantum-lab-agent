# A2：本機一般量子電路

本階段僅使用 Qiskit 2.5.2 / Aer 0.17.2 CPU 模擬，不需要 IBM Runtime、IBM 帳號或 QPU。驗證不呼叫 NVIDIA。`uv sync --locked` 安裝鎖定依賴。

## 可重現入口

```powershell
uv run python scripts/quantum_smoke.py --output .qla/quantum-smoke
uv run qla quantum-tool build_circuit --arguments '{"target":"bell","preset":"bell"}'
uv run qla quantum-tool run_simulation --arguments '{"circuit_id":"<64位雜湊>","shots":1024,"seed":7}'
uv run qla quantum-tool quantum_read_report --arguments '{"result_id":"<64位雜湊>"}'
```

`quantum-tool` 不建立 provider。CLI 的 `--artifact-root` 是操作者設定，工具 JSON 不接受路徑。Python API：`QuantumAdapter(root).execute(name, arguments, deadline)`，deadline 使用 `time.monotonic()`。同步科學操作透過 `asyncio.to_thread` 執行。

Agent 設定：`qla --profile lmstudio run --family quantum --artifact-root .qla/quantum --prompt "建立並驗證 Bell，模擬並繪圖" --max-tools 8 --max-steps 8`。此指令會連線指定的 LLM；本次只測 fake provider。`--profile` 選 LLM；`--family` 選工具集合。預設 `qec` 保持相容。量子 family 不接受 QEC 的 `--finalize-on-report` / `--report-count`。沒有量子自動 report-count 政策。

## 工具契約

* `build_circuit`: `qubits` 2–6，`target` bell/ghz；`preset` bell/ghz 或 `gates` 二擇一。Bell 限兩 qubits。明確 gate 例如 `{"name":"cx","qubits":[0,1]}`、`{"name":"ry","qubits":[0],"angle":1.2}`。
* 只支援 h/x/y/z/s/sdg/cx/cz/rx/ry/rz，最多 64 gates，旋轉角為有限弧度，索引有效且雙 qubit gate 不重複。沒有 Python、QASM、eval 或自訂 gate。
* `verify` / `analyze`: `circuit_id`。
* `run_simulation`: `circuit_id`、`mode` ideal/noisy、`shots` 1–8192、32-bit 非負 `seed`，`noise` 包含 depolarizing_1q / depolarizing_2q / readout，皆 0–1。
* `plot` / `quantum_read_report`: `result_id`。繪圖輸出電路及 histogram，各 SVG/PNG。

## 科學定義與限制

目標獨立定義為 `( |00…0⟩ + |11…1⟩ ) / √2`，不是從待測電路產生。理想 premeasurement fidelity 的通過門檻固定 0.999999。失敗回傳 `verification.status=target_mismatch`，Agent 可修正 gate；每 run 最多三次 build，第一次鎖定 target 與 qubits，不能降低門檻。未修正 mismatch 不標成 completed。不同研究目標使用不同 run。

完成狀態以 circuit ID 綁定理想驗證證據。只有 build 的草稿可由後續 build 取代；一旦 verify、simulation、report read、analyze 或 plot 使用某電路，該電路的理想驗證會保留為本次 run 的相關證據。任一相關電路 mismatch，模型停止時回傳 `target_mismatch`，Agent CLI exit code 為 1；之後建立另一個正確電路不會掩蓋先前已使用的錯誤電路。跨 run 讀取既存 artifacts 也重新計算理想驗證，不使用 noisy fidelity 判斷 build 正確性。

模擬以 density matrix 算 fidelity，以 finite shots 產生 counts；**counts 不能證明 quantum fidelity**。Readout 是獨立對稱 classical bit flip，只影響 counts。Aer depolarizing channel 使用 `E(ρ)=(1-p)ρ+p I/2^n`，在每個原始一／二 qubit gate 後施加對應參數；不先最佳化或改 basis。噪音降低 fidelity 不代表 build 錯誤。bitstring 為 `q[n-1]…q[0]`，q0 最低位。

資源統計另行實際 transpile：basis rz/sx/x/cx、optimization_level=0、seed_transpiler=7、全連通、不含 measurement、無硬體 routing 或 duration。Bell 為 rz×2、sx×1、cx×1，depth 4；不是原始 gate 名稱估算。6-qubit density matrix 本體 65,536 bytes，Aer 記憶體設定 64 MiB、單執行緒；不含 Python/繪圖開銷。timeout 不會強制殺死已啟動的 worker，但單次工作受 qubits/gates/shots 限制。

JSON artifact 以 SHA-256 定址，記錄 circuit spec、target 定義、版本、seed、noise 設定、matrix、counts、資源假設。讀取會檢查內容雜湊與 family/type；圖檔 manifest 記錄檔名及 SHA-256。固定量子 renderer 與 QEC schema 分離。SHA-256 是完整性檢查，不是來源數位簽章；artifact root 由本機操作者信任管理。SVG/PNG bytes 可能含繪圖時間等 metadata，不保證跨次繪圖同 hash。

## 本機證據

`scripts/quantum_smoke.py` 產生 Bell、GHZ3 的 ideal/readout/gate-noise 共六筆實測，逐筆讀回報告並驗證圖檔引用。`smoke-summary.json` 含完整 artifact references。`docs/notebooks/a2-local.ipynb` 可互動重跑。不使用真實模型輸出作科學正確性依據。

參考 API：
* https://docs.quantum.ibm.com/api/qiskit/quantum_info#state-fidelity
* https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html
* https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.depolarizing_error.html
