#!/bin/bash
#SBATCH --job-name=graph-frontier-holdouts
#SBATCH --partition=mi355x
#SBATCH --nodelist=marlowe-mi355x-2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919/slurm-%j.log
set -euo pipefail
srun --ntasks=1 --container-name=hisparse-preview-48593 --container-writable --container-mounts=/workspace:/workspace,/local:/local --container-workdir=/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919 --no-container-entrypoint --container-remap-root --no-container-mount-home python3 holdouts-v7/run.py --spec holdouts-v7-spec.json --out "holdouts-j${SLURM_JOB_ID}"
