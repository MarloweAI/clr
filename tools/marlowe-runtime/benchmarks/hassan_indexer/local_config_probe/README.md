# Same-byte configuration checkpoint

This frozen campaign reuses the exact v3 HIP/private-HSA package from graph_local_tokens_probe. The four source/build receipt symlinks point to that existing immutable checkpoint to avoid duplicating the same runtime patches/manifests. Benchmark/runner/fixtures are kept byte-for-byte as used in55272. Actual library bytes and complete raw results remain at the paths in LOCAL_CONFIG_RESULTS.md. Keep the sibling checkpoint when copying this archive.
