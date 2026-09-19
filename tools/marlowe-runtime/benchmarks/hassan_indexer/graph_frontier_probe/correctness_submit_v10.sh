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
srun --ntasks=1 --container-name=hisparse-preview-48593 --container-writable --container-mounts=/workspace:/workspace,/local:/local --container-workdir=/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919 --no-container-entrypoint --container-remap-root --no-container-mount-home bash -c 'python3 boundary_transition_v10.py --out "transition-j${SLURM_JOB_ID}" && python3 preflight_boundary_v8.py --out "preflight-j${SLURM_JOB_ID}" --revision v10 && python3 ownership_boundary_v8.py --out "ownership-checks-j${SLURM_JOB_ID}" --revision v10 && python3 capacity_boundary_v8.py --out "capacity-j${SLURM_JOB_ID}" --revision v10'
