# Build inputs for junos_then_action_conflicts

The 108-term IMPORT policy on dut and the matching tag-and-export
policy on sender are too large to deploy as a single startup config
(commit fails at boot, leaving SSH unreachable). The build process is:

1. **Boot minimal**: containerlab deploys with `bootstrap/dut.cfg`,
   `bootstrap/sender.cfg`, and `../configs/collector.cfg` (collector's
   config is small enough to ship as the final form).

2. **Probe**: `python3 push-terms.py probe-dut`
   - Bulk-pushes all 108 dut terms via `load set terminal`.
   - Runs `commit check`. If it fails, binary-searches the term set
     to isolate each rejection.
   - Writes `commit-results.yaml` with per-term outcome.

3. **Apply**: `python3 push-terms.py apply-dut` and
   `python3 push-terms.py apply-sender`
   - Pushes the surviving terms (101 on dut, 108 on sender).
   - Commits.

4. **Standard**: `lab_builder validate` + `collect` + `build-snapshot`.

After all steps, `../configs/dut.cfg` and `../configs/sender.cfg`
are the post-commit retained config (FULL form, with `/* COMMIT-REJECTED */`
blocks for the 7 rejected terms).

## Files

| File                  | Purpose                                                                                                                                                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest-N-*.yaml`   | Per-section term definitions (see lab plan §1–§7)                                                                                                                                                                             |
| `term-metadata.yaml`  | Flat aggregation of all 108 terms (generated)                                                                                                                                                                                 |
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
