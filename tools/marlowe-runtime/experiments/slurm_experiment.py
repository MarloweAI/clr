#!/usr/bin/env python3
"""Submit once, then observe Slurm without cancel/restart; exit 75 requests inspection."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

TERMINAL = {'COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', 'OUT_OF_MEMORY',
            'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL', 'DEADLINE', 'REVOKED'}


def accounting(text, job_id):
    for line in text.splitlines():
        fields = line.split('|')
        if len(fields) >= 3 and fields[0] == str(job_id):
            return fields[1].split()[0].rstrip('+'), fields[2]
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', required=True)
    p.add_argument('--receipt', type=Path, required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--submit-script')
    g.add_argument('--job-id', type=int)
    p.add_argument('--remote-workdir')
    p.add_argument('--log', help='Remote log path; {job_id} is expanded after submission')
    p.add_argument('--validate', help='Explicit remote validation command after Slurm COMPLETED 0:0')
    p.add_argument('--queue-inspect-s', type=float, default=600)
    p.add_argument('--startup-inspect-s', type=float, default=300)
    p.add_argument('--run-inspect-s', type=float, default=1200)
    p.add_argument('--stall-inspect-s', type=float, default=600)
    p.add_argument('--poll-s', type=float, default=30)
    a = p.parse_args()
    for v in (a.queue_inspect_s, a.startup_inspect_s, a.run_inspect_s,
              a.stall_inspect_s, a.poll_s):
        if v <= 0: p.error('durations must be positive')
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    lock = open(str(a.receipt) + '.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        p.error('another monitor owns this receipt')
    state = json.loads(a.receipt.read_text()) if a.receipt.exists() else {'host': a.host}
    if state['host'] != a.host: p.error('receipt host differs')

    def save():
        tmp = a.receipt.with_suffix(a.receipt.suffix + '.tmp')
        with tmp.open('w') as f:
            json.dump(state, f, indent=2)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, a.receipt)

    def emit(event, **kw):
        record = dict(event=event, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **kw)
        state['last_event'] = record
        save()
        print(json.dumps(record), flush=True)

    def remote(cmd, timeout=40):
        r = subprocess.run(['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'IdentityAgent=none',
                            '-o', 'ConnectTimeout=15', a.host, cmd],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode:
            raise RuntimeError(f'remote exit {r.returncode}: {r.stderr[-1500:]}')
        return r.stdout

    if not state.get('job_id'):
        if state.get('submission_attempted'):
            emit('INSPECT', reason='previous submission result is unknown; reconcile Slurm before attaching job ID')
            if not a.job_id: return 75
        if a.job_id:
            state.update(job_id=a.job_id, log=a.log or state.get('log'),
                         validate=a.validate or state.get('validate'))
        elif a.submit_script:
            if not a.remote_workdir: p.error('--remote-workdir required for submission')
            # Journal intent before network call: interruption must never cause an automatic resubmit.
            state.update(submission_attempted=True, script=a.submit_script,
                         remote_workdir=a.remote_workdir, validate=a.validate, log=a.log)
            save()
            try:
                out = remote('cd ' + shlex.quote(a.remote_workdir) + ' && sbatch --parsable ' +
                             shlex.quote(a.submit_script))
                if not re.fullmatch(r'\d+(?:;[\w.-]+)?\s*', out):
                    raise RuntimeError('unrecognized sbatch response: ' + out[-500:])
                state['job_id'] = int(out.split(';')[0].strip())
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                emit('INSPECT', reason=str(e), submission_may_have_succeeded=True)
                return 75
        else:
            p.error('new receipt requires --submit-script or --job-id')
        save()
        emit('ATTACHED', job_id=state['job_id'])
    elif a.job_id and a.job_id != state['job_id']:
        p.error('job ID differs from existing receipt')
    job = state['job_id']
    log = a.log or state.get('log')
    validate = a.validate or state.get('validate')
    if log: log = log.format(job_id=job)
    if state.get('validation_passed'):
        emit('COMPLETE', job_id=job, validation='already passed')
        return 0
    # Each invocation grants a new observation window, while preserving the same job.
    # Soft deadlines are deliberately separate from the script's Slurm --time limit.
    started = time.monotonic()
    running_since = None
    progress_since = started
    progress = None
    last_status = None
    seen_output = False
    while True:
        try:
            rows = remote(f'squeue -h -j {job} -o "%i|%T|%R"')
            queue = [s.split('|', 2) for s in rows.splitlines() if s.split('|')[0] == str(job)]
            rec = accounting(remote(f'sacct -X -n -P -j {job} --format=JobIDRaw,State,ExitCode'), job)
            if rec and rec[0] in TERMINAL:
                state.update(slurm_state=rec[0], slurm_exit=rec[1])
                if rec != ('COMPLETED', '0:0'):
                    emit('FAILED', job_id=job, slurm_state=rec[0], slurm_exit=rec[1])
                    return 1
                emit('VALIDATING', job_id=job)
                if validate:
                    # Validation timeout also requests inspection, never job cancellation.
                    output = remote(validate, timeout=120)
                    state['validation_output'] = output[-12000:]
                state['validation_passed'] = True
                emit('COMPLETE', job_id=job, validation='passed' if validate else 'Slurm only; no artifact validation supplied')
                return 0
            status = queue[0][1] if queue else (rec[0] if rec else 'ACCOUNTING_PENDING')
            if status != last_status:
                emit('STATE', job_id=job, state=status, reason=queue[0][2] if queue else '')
                last_status = status
            now = time.monotonic()
            if status in ('RUNNING', 'COMPLETING'):
                if running_since is None: running_since = now
                if log:
                    stamp = remote('if test -f ' + shlex.quote(log) + '; then stat -c "%s:%Y" ' + shlex.quote(log) + '; fi').strip()
                    if stamp and stamp != progress:
                        progress, progress_since = stamp, now
                        seen_output = int(stamp.split(':')[0]) > 0
                reason = None
                if not seen_output and log and now - running_since >= a.startup_inspect_s:
                    reason = 'startup observation deadline (no nonempty log)'
                elif now - running_since >= a.run_inspect_s:
                    reason = 'execution observation deadline'
                elif seen_output and now - progress_since >= a.stall_inspect_s:
                    reason = 'log progress observation deadline'
                if reason:
                    emit('INSPECT', job_id=job, reason=reason, log=log)
                    return 75
            elif now - started >= a.queue_inspect_s:
                emit('INSPECT', job_id=job, reason='queue/accounting observation deadline', state=status)
                return 75
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as e:
            emit('INSPECT', job_id=job, reason=str(e))
            return 75
        time.sleep(a.poll_s)


if __name__ == '__main__':
    raise SystemExit(main())
