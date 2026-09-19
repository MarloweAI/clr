# Receipt parser correction after55209

Job55209 exited1:0 during the audit of its fourth fixture. The fixture process exited0 and all six numerical/update/disable/destruction cases passed. The final callback receipt is present inside the multi-call LANE_FIXTURE_END output line; a startswith-based parser incorrectly ignored it.

The corrected parser finds complete GRAPH_LOCAL_ marker-delimited runtime records anywhere on a physical line. Every runtime record is a single newline-terminated fprintf. No count, packet, callback, generation-reuse or mapped-library check is relaxed. Revalidating the unchanged failed log recovers all four begins/completions/retirements and36 original packets. Original failed artifacts and the exact prior harness are retained under results-j55209 and harness-j55209. Runtime v3/HIP69f3/HSA2899 bytes remain unchanged for the retry.
