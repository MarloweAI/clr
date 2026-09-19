#!/bin/bash
#SBATCH --job-name=graph-frontier-timestamps
#SBATCH --partition=mi355x
#SBATCH --nodelist=marlowe-mi355x-2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919/preflight-slurm-%j.log
set -euo pipefail
srun --ntasks=1 --container-name=hisparse-preview-48593 --container-writable --container-mounts=/workspace:/workspace,/local:/local --container-workdir=/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919 --no-container-entrypoint --container-remap-root --no-container-mount-home bash -c 'python3 preflight.py --out "preflight-j${SLURM_JOB_ID}" --revision v4 && python3 timestamps.py --out "timestamps-j${SLURM_JOB_ID}" --revision v4'
