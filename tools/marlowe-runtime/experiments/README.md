# Scripted experiment ownership

Use `slurm_experiment.py` for short and long experiments. It journals submission
intent before `sbatch`, saves the returned job ID, owns a lock on the receipt, and
polls Slurm in Python. It does not launch a second job when submission succeeded
but its reply was lost. Reconcile Slurm, then attach the confirmed ID instead.

```bash
python3 slurm_experiment.py --host marlowe-login1 \
  --receipt /absolute/local/experiment/job.json \
  --submit-script submit.sh --remote-workdir /absolute/remote/experiment \
  --log '/absolute/remote/experiment/slurm-{job_id}.log' \
  --validate 'python3 /absolute/remote/experiment/audit.py {job_id}' \
  --queue-inspect-s 600 --startup-inspect-s 300 \
  --run-inspect-s 1800 --stall-inspect-s 600
```

Keep the execution handle and let the script wait. Exit 0 means Slurm completed
with exit `0:0` and the supplied validator passed; without a validator this means
Slurm success only. Exit 1 reports a terminal unsuccessful job. Exit 75 requests
inspection: an observation deadline, status-query problem, failed validator or
unknown submission result. **No path cancels or restarts a job.** Slurm's hard
`--time` limit is a separate, explicit setting in the submitted script.

Choose deadlines from expected queue delay, startup/JIT and work duration: a short
microbenchmark should wake for inspection sooner than a model load and three
resident trials. Log activity is only a progress hint, not proof of useful work.
Inspect the same job when a deadline fires. If healthy, run the monitor again with
the same receipt and adjusted deadlines; its observation window resets, its job
ID does not. Completed validation is recorded and not repeated automatically.
Do not add a second watcher or an agent that merely polls the same job.

`{job_id}` in the validation command expands to the attached Slurm ID, so the
validator can require that exact job's artifacts. Other command braces are preserved.

Raw output, launch receipts, runtime/source hashes and validation artifacts belong
in the experiment directory outside the repository. All timing trials, including
long ones, remain in the audit. Set `--validate` to check exact cell coverage,
correctness and mapped runtime identity, not just existence of a success file.
