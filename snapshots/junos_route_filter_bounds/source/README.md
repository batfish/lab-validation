# Junos route-filter bounds

Single-node vJunos-router lab on Junos 25.4R1.12. It tests all seven
route-filter match types with IPv4 and IPv6 prefixes, including empty
ranges, host prefixes, host bits, noncontiguous masks, address-family
mismatches, and overlapping filters.

`cases.json` defines the experiments. `candidates.json` lists 38 active
static discard routes. Each experiment loads its policy, runs `commit
check`, commits if the check passes, and evaluates the policy against
the device RIB with `test policy`. An explicit reject term prevents
default policy behavior from accepting unmatched routes.

## Findings

- `upto` below the base prefix length commits without warnings and
  matches nothing. This includes `/26 upto /24`.
- `longer` on `/32` or `/128` commits without warnings and matches
  nothing.
- A reversed `prefix-length-range` commits without warnings and matches
  nothing when its minimum is valid. A minimum below the base length
  or either length above the address-family limit fails commit check.
- `through` with a shorter endpoint fails commit check. An endpoint
  outside the base prefix commits without warnings and matches nothing,
  including when the endpoint is present in the RIB.
- An `address-mask` whose leading contiguous ones exceed the base
  length fails commit check. Noncontiguous masks are allowed; the total
  number of set bits is not the limit. Longest-prefix lookup also uses
  the mask's leading contiguous ones.
- Mismatched address families for `through` and `address-mask` fail
  commit check.
- Host bits in `exact` and `address-mask` filters are accepted and
  normalized for matching.
- An empty filter still participates in longest-prefix lookup. A
  `/26 upto /24` prevents routes under that `/26` from falling back to
  a broader `/24 orlonger` in the same term.

The complete matrix is in [results.md](results.md). Device transcripts,
including all errors, are in `../show/dut/route_filter_tests/`. No experiment produced a
warning while loading, checking, or committing its policy.

Batfish reports rejected configurations as FATAL and committed,
impossible matches as RISK. Its IPv4 conversion preserves empty
filters' suppression of broader matches. IPv6 observations verify
diagnostics; Batfish does not model IPv6 routing-policy evaluation.

## Reproduce

Run from the repository root on the lab host:

```bash
sudo containerlab deploy -t snapshots/junos_route_filter_bounds/source/topology.clab.yml
PYTHONPATH=src python -m lab_builder health-check snapshots/junos_route_filter_bounds/source/topology.clab.yml
PYTHONPATH=src python snapshots/junos_route_filter_bounds/source/probe.py --output-dir snapshots/junos_route_filter_bounds/show/dut/route_filter_tests
PYTHONPATH=src python -m lab_builder collect snapshots/junos_route_filter_bounds/source/topology.clab.yml --output-dir working/junos_route_filter_bounds
PYTHONPATH=src python -m lab_builder build-snapshot snapshots/junos_route_filter_bounds/source/topology.clab.yml --name junos_route_filter_bounds --collected-dir working/junos_route_filter_bounds --snapshots-dir snapshots
python snapshots/junos_route_filter_bounds/source/create_expectations.py
```

`probe.py --case <name>` selects a case and can be repeated to select
several. It verifies that every candidate is in the RIB before testing.
`create_expectations.py` requires a complete run and derives the IPv4
policy expectations from the device output. Its optional
`--batfish-resources` argument regenerates Batfish's unit-test fixtures.

With the updated Batfish service running:

```bash
pytest lab_tests/test_labs.py --labname=junos_route_filter_bounds
```

`validation/routing_policy_matches.json` contains the node, input route
prefixes, and the prefixes accepted by each policy. The policy test checks
every policy against every candidate, including rejected routes.

`configs/case-*/case.cfg` contains generated parser inputs for all 93
experiments, including configurations that Junos rejected. These are
fixtures, not collected device configurations. The collected router
configuration remains under `configs/dut/`.

The existing `test_parse_warnings` test checks
`validation/parse_warnings.yaml` for every fixture: 28 FATAL cases,
25 RISK cases, and 40 controls with no warnings. It also checks all 25
RISK warnings on the collected router configuration. `strict: true`
rejects missing, duplicate, misclassified, and additional red flags.
Configuration-format checks run for every fixture. Device-state
comparisons run on `dut`; the fixtures have no collected device state
and are excluded from those comparisons using the existing sickbay
mechanism.
