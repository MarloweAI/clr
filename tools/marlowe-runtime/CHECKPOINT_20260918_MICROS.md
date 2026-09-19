# Fresh microbenchmark checkpoint — job53652

All313aggregate cells and all process trials retained. Original52217binary/reference/protocol hashes; four balanced orders. Values are medians of process medians. No instrumentation or runtime rebuild.

| Family | Cells | Previous vs stock wins / within2% / losses | Covered parallel vs stock | Covered one-stream vs stock |
|---|---:|---:|---:|---:|
| grouped_s1 | 12 | 0 / 12 / 0 | 0 / 12 / 0 | 0 / 12 / 0 |
| queued | 8 | 0 / 8 / 0 | 0 / 8 / 0 | 0 / 8 / 0 |
| fanout_q4 | 6 | 3 / 3 / 0 | 3 / 3 / 0 | 3 / 3 / 0 |
| fanout_q8 | 6 | 3 / 3 / 0 | 3 / 3 / 0 | 3 / 3 / 0 |
| attention_fetch | 120 | 0 / 120 / 0 | 0 / 109 / 11 | 0 / 102 / 18 |
| pipeline | 36 | 0 / 35 / 1 | 0 / 36 / 0 | 0 / 35 / 1 |
| mixed | 16 | 0 / 16 / 0 | 0 / 16 / 0 | 0 / 14 / 2 |
| grouped_s22 | 12 | 12 / 0 / 0 | 12 / 0 / 0 | 12 / 0 / 0 |
| experts | 52 | 9 / 42 / 1 | 11 / 41 / 0 | 7 / 39 / 6 |
| dispatch | 42 | 0 / 42 / 0 | 2 / 40 / 0 | 1 / 32 / 9 |
| waiter | 3 | 1 / 2 / 0 | 1 / 2 / 0 | 1 / 2 / 0 |

Waiter excess removal: stock 0.000%, previous 95.769%, covered 96.048%, serial 96.016%

| Representative graph workload | Stock us | Previous RC1 us | Covered parallel us | Covered one-stream us |
|---|---:|---:|---:|---:|
| experts b16-balanced 2_streams | 230.417 | 229.748 | 226.068 | 411.394 |
| experts b16-balanced 4_streams | 235.138 | 158.065 | 150.145 | 412.183 |
| experts b64-balanced 2_streams | 114.333 | 117.104 | 110.093 | 168.975 |
| experts b64-balanced 4_streams | 117.193 | 101.124 | 93.843 | 169.276 |
| experts b64-skewed 4_streams | 193.027 | 164.146 | 155.725 | 308.540 |
| attention_fetch h32-miss128-r1152 gather-parallel | 701.252 | 708.801 | 702.051 | 752.763 |
| pipeline h32-l32-miss128 two_streams | 8602.128 | 8604.176 | 8605.715 | 8603.045 |
| mixed matrix-kv parallel | 217.737 | 218.527 | 219.587 | 263.599 |

covered aggregate primary-metric losses above2% versus stock:

| Cell | Change | Per-round changes |
|---|---:|---|
| attention_fetch / h128-miss128-r1152 / memcpy / copy / eager | +6.751% | -9.12%, +13.38%, +19.31%, -0.88% |
| attention_fetch / h128-miss128-r1152 / memcpy-parallel / total / eager | +2.400% | -4.58%, +6.20%, +4.65%, +0.20% |
| attention_fetch / h128-miss128-r1152 / memcpy-serial / total / eager | +2.032% | -2.65%, +3.62%, +4.48%, +0.21% |
| attention_fetch / h32-miss128-r1152 / memcpy / copy / eager | +7.030% | -12.43%, +14.14%, +18.32%, -0.13% |
| attention_fetch / h32-miss128-r1152 / memcpy-parallel / total / eager | +2.257% | -3.98%, +4.86%, +5.54%, +0.02% |
| attention_fetch / h32-miss128-r584 / memcpy / copy / eager | +6.910% | -12.53%, +14.00%, +15.31%, -0.65% |
| attention_fetch / h32-miss128-r584 / memcpy-parallel / total / eager | +2.181% | -3.72%, +6.43%, +4.36%, -0.59% |
| attention_fetch / h32-miss256-r1152 / memcpy / copy / eager | +7.846% | -12.17%, +15.39%, +17.22%, -0.56% |
| attention_fetch / h32-miss256-r1152 / memcpy-parallel / total / eager | +3.437% | -6.37%, +6.66%, +10.04%, -0.76% |
| attention_fetch / h32-miss256-r1152 / memcpy-serial / total / eager | +2.889% | -5.00%, +5.58%, +6.91%, -0.37% |
| attention_fetch / h32-miss32-r1152 / memcpy / copy / eager | +6.056% | -11.37%, +11.33%, +16.06%, +0.80% |

serial aggregate primary-metric losses above2% versus stock:

| Cell | Change | Per-round changes |
|---|---:|---|
| attention_fetch / h128-miss128-r1152 / gather-parallel / total / graph | +6.514% | +6.04%, +6.53%, +6.50%, +7.29% |
| attention_fetch / h128-miss128-r1152 / memcpy / copy / eager | +5.125% | -0.19%, +0.25%, +10.62%, -0.37% |
| attention_fetch / h128-miss128-r1152 / memcpy-parallel / total / eager | +2.568% | +0.53%, +1.26%, +3.93%, -0.03% |
| attention_fetch / h32-miss128-r1152 / gather-parallel / total / graph | +7.346% | +6.56%, +7.19%, +7.85%, +7.42% |
| attention_fetch / h32-miss128-r1152 / memcpy / copy / eager | +4.646% | -2.87%, -1.10%, +12.25%, -0.40% |
| attention_fetch / h32-miss128-r1152 / memcpy-parallel / total / eager | +2.825% | +1.48%, +0.47%, +5.62%, -0.73% |
| attention_fetch / h32-miss128-r584 / gather-parallel / total / graph | +6.704% | +6.72%, +6.69%, +6.51%, +7.05% |
| attention_fetch / h32-miss128-r584 / memcpy / copy / eager | +7.786% | +2.07%, +0.57%, +15.27%, -0.70% |
| attention_fetch / h32-miss128-r584 / memcpy-parallel / total / eager | +2.649% | +1.42%, -0.12%, +5.63%, +0.15% |
| attention_fetch / h32-miss128-r584 / memcpy-serial / total / eager | +2.005% | +0.97%, +0.02%, +4.36%, +0.35% |
| attention_fetch / h32-miss256-r1152 / gather / merge / graph | +2.108% | +3.29%, +1.71%, +1.24%, +0.00% |
| attention_fetch / h32-miss256-r1152 / gather-parallel / total / graph | +14.709% | +14.11%, +14.84%, +14.99%, +15.16% |
| attention_fetch / h32-miss256-r1152 / memcpy / copy / eager | +7.617% | +0.84%, +0.15%, +17.48%, -0.38% |
| attention_fetch / h32-miss256-r1152 / memcpy / copy / graph | +2.033% | +1.98%, +2.00%, +0.03%, +2.10% |
| attention_fetch / h32-miss256-r1152 / memcpy-parallel / total / eager | +3.040% | -0.83%, -0.05%, +8.11%, -0.10% |
| attention_fetch / h32-miss256-r1152 / memcpy-parallel / total / graph | +2.222% | +0.29%, +2.57%, +0.60%, +2.25% |
| attention_fetch / h32-miss256-r1152 / memcpy-serial / total / eager | +2.444% | -0.60%, +0.07%, +5.27%, +0.29% |
| attention_fetch / h32-miss32-r1152 / memcpy / copy / eager | +7.512% | +2.61%, +0.91%, +16.78%, -0.08% |
| dispatch / 256 / 1024 / 1 / graph / parallel | +65.988% | +63.30%, +68.34%, +65.77%, +65.16% |
| dispatch / 256 / 1024 / 16 / graph / parallel | +98.773% | +100.08%, +95.99%, +100.61%, +97.63% |
| dispatch / 256 / 1024 / 256 / graph / parallel | +94.980% | +96.38%, +94.74%, +94.50%, +94.18% |
| dispatch / 256 / 1024 / 4 / graph / parallel | +91.274% | +85.39%, +92.69%, +92.75%, +89.44% |
| dispatch / 256 / 256 / 1 / graph / parallel | +20.917% | +21.33%, +21.10%, +21.36%, +20.50% |
| dispatch / 256 / 256 / 16 / graph / parallel | +92.096% | +90.98%, +92.33%, +93.16%, +92.14% |
| dispatch / 256 / 256 / 256 / graph / parallel | +94.732% | +94.49%, +94.89%, +95.19%, +94.20% |
| dispatch / 256 / 256 / 4 / graph / parallel | +63.091% | +64.06%, +64.28%, +61.92%, +62.02% |
| dispatch / 64 / 8192 / 1 / graph / parallel | +85.816% | +85.47%, +86.68%, +85.81%, +85.81% |
| experts / b16-balanced / 2_streams / total / graph | +78.543% | +73.81%, +78.62%, +78.46%, +78.33% |
| experts / b16-balanced / 4_streams / total / graph | +75.294% | +75.78%, +77.09%, +75.20%, +74.54% |
| experts / b64-balanced / 2_streams / total / graph | +47.792% | +46.51%, +53.36%, +48.72%, +46.86% |
| experts / b64-balanced / 4_streams / total / graph | +44.441% | +44.30%, +44.80%, +44.15%, +44.41% |
| experts / b64-skewed / 2_streams / total / graph | +59.406% | +59.01%, +57.82%, +59.81%, +60.52% |
| experts / b64-skewed / 4_streams / total / graph | +59.843% | +60.14%, +52.76%, +59.55%, +61.22% |
| mixed / kv-kv / parallel / total / graph | +10.286% | +10.20%, +8.96%, +10.08%, +10.63% |
| mixed / matrix-kv / parallel / total / graph | +21.063% | +21.15%, +18.69%, +21.50%, +21.15% |
| pipeline / h128-l8-miss128 / isolated / h2d / eager | +2.253% | -3.30%, +2.78%, +2.15%, +3.02% |

Original Hassan Q/K:

| Setting | GPU us | Host us | Submit us |
|---|---:|---:|---:|
| covered | 22.174016 | 22.218367 | 4.690325 |
| earlier_best | 19.124619 | 19.164380 | 2.577113 |
| previous | 22.105758 | 22.146542 | 4.569700 |
| serial | 19.144268 | 19.184615 | 2.509826 |
| stock | 19.936594 | 19.976830 | 4.720440 |

Preservation: current one-stream / earlier one-stream = +0.103% GPU. Current one-stream / stock = -3.974%.
