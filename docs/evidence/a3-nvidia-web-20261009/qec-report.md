# Quantum Lab Agent

Run: ee0aed7c00234101989131000a72dd8f

Family: qec / Status: report_ready

Fixture: False

## Grounded evidence

{"result": {"artifact_id": "dataset-af053975eb3844168aafdb6280e1d086", "job_id": "job-6b10765acb4843b3ae76008071b624cd", "status": "succeeded"}, "tool": "qec_sample"}

{"result": {"artifact_id": "checkpoint-7e5ac4a2ddcd41fd92d50a5b46d22774", "job_id": "job-9ee9ee3fa32d4a50bf022792a5113f33", "status": "succeeded"}, "tool": "qec_train"}

Comparison [comparison-39e060dbe49440b3bf0b6b5cc1e6309d] dataset [dataset-af053975eb3844168aafdb6280e1d086]
decoder | errors/shots | LER | CI | decode seconds | source
mwpm | 0/32 | 0 | [0, 0.107182715057] | 0.000573199999053 | [comparison-39e060dbe49440b3bf0b6b5cc1e6309d#prediction_0]
lookup | 0/32 | 0 | [0, 0.107182715057] | 0.000110699998913 | [comparison-39e060dbe49440b3bf0b6b5cc1e6309d#prediction_1]
mlp | 3/32 | 0.09375 | [0.0324009626263, 0.242184993358] | 0.000920199996472 | [comparison-39e060dbe49440b3bf0b6b5cc1e6309d#prediction_2]
Small fixed-shot runs are smoke tests, not superiority evidence.