# Build inputs for junos_then_action_conflicts

The 112-term IMPORT policy on dut and the matching tag-and-export
policy on sender are too large to deploy as a single startup config
(commit fails at boot, leaving SSH unreachable). The build process is:

1. **Boot minimal**: containerlab deploys with `bootstrap/dut.cfg`,
   `bootstrap/sender.cfg`, and `../configs/collector.cfg` (collector's
   config is small enough to ship as the final form).

2. **Probe**: `python3 push-terms.py probe-dut`
   - Bulk-pushes all 112 dut terms via `load set terminal`.
   - Runs `commit check`. If it fails, binary-searches the term set
     to isolate each rejection.
   - Writes `commit-results.yaml` with per-term outcome.

3. **Apply**: `python3 push-terms.py apply-dut` and
   `python3 push-terms.py apply-sender`
   - Pushes the surviving terms (currently all 112 on this
     vJunos-router build) and commits.

4. **Standard**: `lab_builder validate` + `collect` + `build-snapshot`.

After all steps, `../configs/dut.cfg` and `../configs/sender.cfg`
are the post-commit retained config (FULL form). Any commit-rejected
terms are wrapped in `/* COMMIT-REJECTED */` blocks. On the current
vJunos-router build no terms are rejected at commit time — the
BGP-OUTPUT-QUEUE-PRIORITY actions are silently dropped at load time
(see README §1 rows 24, 25), so the term itself commits cleanly with
only its `accept` retained.

## Files

| File                  | Purpose                                                                                                                                                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest-N-*.yaml`   | Per-section term definitions (see lab plan §1–§7)                                                                                                                                                                             |
| `term-metadata.yaml`  | Flat aggregation of all 112 terms (generated)                                                                                                                                                                                 |
| `assemble.py`         | Reads manifests, writes `term-metadata.yaml` and full configs                                                                                                                                                                 |
| `push-terms.py`       | Drives the probe/apply phases against a running lab                                                                                                                                                                           |
| `commit-results.yaml` | Per-term commit-check outcome (output of `probe-dut`)                                                                                                                                                                         |
| `bootstrap/`          | Minimal bootable configs for containerlab `startup-config`                                                                                                                                                                    |
| `dut.intended.cfg`    | Visual reference: every term as live config, no commit-rejection wrapping. Diff against `../configs/dut.cfg` to see which terms were rejected, and against the snapshot's retained `display set` to see commit-time collapse. |

## Regenerating

```bash
# After editing manifests, regenerate term-metadata.yaml:
python3 assemble.py

# To regenerate the FULL ../configs/dut.cfg and ../configs/sender.cfg
# (with /* COMMIT-REJECTED */ blocks read from commit-results.yaml):
python3 assemble.py --write-configs
```
