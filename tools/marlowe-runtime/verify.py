"""Verify packaged bytes and, when requested, actual libraries in this PyTorch process."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path


def verify(files_only=False):
    root = Path(os.environ.get('MARLOWE_RUNTIME_ROOT', Path(__file__).parent)).resolve()
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, digest in manifest['libraries'].items():
        path = root / 'lib' / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Runtime digest mismatch: {path}')
    if files_only:
        return manifest
    import torch
    torch.cuda.init()
    mapped = {}
    for stem in ('libamdhip64.so', 'libhsa-runtime64.so'):
        paths = {Path(line.split()[-1]).resolve() for line in Path('/proc/self/maps').read_text().splitlines() if stem in line}
        if len(paths) != 1 or next(iter(paths)).parent != root / 'lib':
            raise RuntimeError(f'Unexpected or duplicated runtime: {stem}: {paths}')
        mapped[stem] = str(next(iter(paths)))
    lib = ctypes.CDLL(mapped['libamdhip64.so'])
    version = ctypes.c_int()
    lib.hipRuntimeGetVersion.argtypes = [ctypes.POINTER(ctypes.c_int)]
    lib.hipRuntimeGetVersion.restype = ctypes.c_int
    if lib.hipRuntimeGetVersion(ctypes.byref(version)) != 0 or version.value != 70253211:
        raise RuntimeError(f'Unexpected loaded HIP version: {version.value}')
    devices = [torch.cuda.get_device_properties(i) for i in range(torch.cuda.device_count())]
    if not devices or any(not d.gcnArchName.startswith('gfx950') for d in devices):
        raise RuntimeError('This release is qualified only for gfx950')
    return dict(manifest, mapped=mapped, hip_runtime=version.value, torch=torch.__version__,
                torch_compiled_hip=torch.version.hip, gpu_count=len(devices),
                enabled=os.environ.get('GPU_NATIVE_EVENT_WAIT', '0'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--files-only', action='store_true')
    args = parser.parse_args()
    result = verify(args.files_only)
    if not args.files_only:
        print(json.dumps(result, indent=2))
