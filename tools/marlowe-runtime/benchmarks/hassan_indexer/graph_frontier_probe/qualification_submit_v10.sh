#!/bin/bash
#SBATCH --job-name=graph-frontier-capacity
#SBATCH --partition=mi355x
#SBATCH --nodelist=marlowe-mi355x-2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919/preflight-slurm-%j.log
set -euo pipefail
srun --ntasks=1 --container-name=hisparse-preview-48593 --container-writable --container-mounts=/workspace:/workspace,/local:/local --container-workdir=/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919 --no-container-entrypoint --container-remap-root --no-container-mount-home bash -c 'test -f capacity-j55788/COMPLETE && python3 remaining-boundary/run.py --out "boundary-remaining-j${SLURM_JOB_ID}" && python3 holdouts-boundary/run.py --spec holdouts-boundary-spec.json --out "boundary-holdouts-repeat-j${SLURM_JOB_ID}" && python3 attention-waiter-boundary/run.py --out "boundary-attention-repeat-j${SLURM_JOB_ID}"'
