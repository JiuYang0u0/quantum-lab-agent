# A2 local validation evidence

Validated on Windows / Python 3.12 with Qiskit 2.5.2 and Aer 0.17.2.
Command: `uv run python scripts/quantum_smoke.py`.
All cases use 1024 shots and seed 7. Noise cases use readout=0.1 or gate
depolarizing_1q=0.02 / depolarizing_2q=0.04, respectively.

| Target | Case | Premeasurement fidelity | Counts |
|---|---|---:|---|
| Bell | ideal | 1 | 00:527, 11:497 |
| Bell | readout | 1 | 00:431, 01:83, 10:104, 11:406 |
| Bell | gate noise | 0.9604 | 00:521, 01:6, 10:11, 11:486 |
| GHZ3 | ideal | 1 | 000:527, 111:497 |
| GHZ3 | readout | 1 | 000:383, 001:54, 010:47, 011:49, 100:42, 101:34, 110:39, 111:376 |
| GHZ3 | gate noise | 0.926984 | 000:511, 001:4, 010:7, 011:5, 100:5, 101:21, 110:6, 111:465 |

Resources: exact transpilation into rz/sx/x/cx, optimization 0, seed 7,
all-to-all, no measurements. Bell: rz=2/sx=1/cx=1, depth=4.
GHZ3: rz=2/sx=1/cx=2, depth=5.

Artifacts are retained locally in `.qla/quantum-smoke/`; summary includes every
result and plot-manifest ID. Six plot manifests reference 24 generated graphics
(circuit and histogram, SVG and PNG). Smoke verification reads every report,
checks fixed renderer stability and every graphic SHA-256.

Stable result IDs:

* Bell ideal: `bae9355cb6b2e306ec54cb8a42c1fecb94422aa63e5db8ca966f0019aeb5fd30`
* Bell readout: `641ff518aa49564057e476c3683b2ecf1711ddce762cfbc512fd102f78a43f70`
* Bell gate noise: `38b1485d9afa9ecb627abce1fd0ee5d868dc6fe4140de825dc2a9618be0498ec`
* GHZ3 ideal: `e3ea780e0223119259707a1123df9462968fbf5c4c716417a6f8e2d6b9b9021c`
* GHZ3 readout: `d19e24e48e999deb5abbdb0d2557e8c1468f9ca42ebab82514a6b34f8b5dbfa5`
* GHZ3 gate noise: `64b65a16043cd38d502e4e85859fc730e3f219b6c8ce278d49b91e96105b0080`

The original offline validation below used no live model or QPU. Subsequent
[2026-10-08 NVIDIA evaluation](evidence/a2-nvidia-20261008.md) passed both approved
native model cases in nine completions; no QPU validation has been performed.
Offline provider orchestration uses a
deterministic fake model that first constructs the wrong Bell circuit and then
corrects it without changing target. Phase-error testing demonstrates equal
counts but fidelity 0 versus 1. Readout invariance and p=0 consistency are tested.
