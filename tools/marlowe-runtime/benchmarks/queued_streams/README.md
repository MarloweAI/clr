# Queued attention and fragmented-producer fanout

A performance review identified a hole in per-trial synchronization: a host can
submit many short fork/join stages before the GPU executes the first wait. A
256-kernel history can then approve a wait whose remaining producer work is short
when that wait finally executes. This benchmark keeps that submission pattern
visible. It uses one allocated gfx950 GPU.

`queued_chains` reuses the attention arithmetic and independent CPU oracle from
`attention_stream_chains`. It compares depth 1 with 16 complete attention steps
submitted before a single final synchronization. Each step has separate query,
summary, timestamp and event storage, and all outputs are checked. Balanced and
7/8-uneven 64-stage chains use two and four streams. All branches feed the next
query update. Per-step GPU time and whole-batch host time are separate metrics;
branch spans, branch envelopes, start skew and join gaps remain in the CSV.

`fanout` submits 2,048 increment kernels in 128-kernel graph chunks separated by
already-complete event waits, then joins one, two or three consumer streams. It
checks every consumer's result. Queue caps 4 and 8 test the available distinct
queues. A separate cell places a controlled 5 ms kernel on each consumer before
its event wait, testing late execution after early host admission. This delay is
a scheduling control, not an attention kernel or useful-work speedup claim.

```bash
python3 run.py --candidate-lib /path/to/candidate/lib \
  --previous-lib /path/to/v8/lib --output /path/to/new-results
```

Stock, candidate off/on and previous-on execute in rotated order across three
fresh-process rounds. There are 36 processes and 5,904 measured rows. The runner
checks HIP/HSA mappings, records source/binary/library hashes and keeps every
sample. Separate diagnostic runs record native packet counts and are excluded
from timing comparisons. The declared performance screen flags a headline metric
if on is over 2% slower than a control in all three paired rounds. Component gaps
are reported separately: longer handoff can coexist with faster producer and
overall execution. A finite screen does not prove universal neutrality.

The initially tested unrestricted history candidate passed the previous suite but
failed this queued-work test: balanced two-stream depth 16 changed from 3.174 to
5.941 ms per step; depth 1 was neutral. The pending-dependency segment guard removes
that admission in the first corrected prototype. See the release qualification
report for exact final bytes and results; prototype measurements do not qualify a
subsequent build.

[Final v9 RC2 results](RESULTS.md) record the committed-source package checks.
