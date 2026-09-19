#!/bin/bash
#SBATCH --job-name=hassan-aql-layer
#SBATCH --partition=mi355x
#SBATCH --nodelist=marlowe-mi355x-2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/workspace/home/sasha/amd-runtime-production/iterations/hassan-same-queue-20260919/pilot/slurm-%j.log
set -euo pipefail
srun --ntasks=1 --container-name=hisparse-preview-48593 --container-writable --container-mounts=/workspace:/workspace,/local:/local --container-workdir=/workspace/home/sasha/amd-runtime-production/iterations/hassan-same-queue-20260919/pilot --no-container-entrypoint --container-remap-root --no-container-mount-home bash run.sh
