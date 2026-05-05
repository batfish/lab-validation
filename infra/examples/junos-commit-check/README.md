# Junos Commit Check Lab

Tests which Junos configuration syntax is rejected at commit time due to
unnormalized prefixes (host bits set). Results drive Batfish's
`fatalRedFlag` implementation for Junos prefix validation.

## Background

Junos performs "commit checks" that reject certain config at commit time
even though `set` commands accept it. For example, `set routing-options
static route 10.0.0.5/8 reject` is accepted by the CLI but rejected at
commit because the prefix has host bits set.

Batfish models this with `fatalRedFlag` warnings (see batfish/batfish#9928).
This lab empirically determines which `ip_prefix` grammar contexts enforce
normalization and which do not.

## Methodology

Single vJunos-router node. For each grammar rule that accepts `ip_prefix`
or `ip_prefix_default_32`, we attempt to commit `192.168.1.111/24` (host
bits set) via `commit check`. The device either rejects it or accepts it.

The `checks.yaml` uses two check types:

- `commit_check_rejects`: asserts `commit check` fails
- `commit_check_accepts`: asserts `commit check` succeeds

Each check loads config lines, runs `commit check`, and rolls back.

## Running

```bash
# On EC2 with containerlab + vJunos image:
sudo containerlab deploy -t topology.clab.yml
# Wait for health (~5 min)
python3 run_commit_checks.py checks.yaml 172.20.20.2 admin "admin@123"
```

## Results (vJunos 25.4R1.12)

**Rejects host bits:**

- `routing-options static route`
- `routing-options aggregate route`
- `routing-options generate route`
- `protocols ospf area X area-range`
- `firewall filter X term T from destination-address`
- `firewall filter X term T then next-ip`
- `policy-options condition X if-route-exists`

**Accepts host bits:**

- `policy-options prefix-list`
- `policy-options policy-statement X from route-filter`
- `snmp client-list`
- `protocols bgp group X allow`
- `protocols mpls label-switched-path X install`
- `interfaces X unit Y family inet address`
- `interfaces X unit Y family inet address A vrrp-group N track route`

**Not tested (requires vSRX):**

- `security nat` (pool address, match address, static-nat prefix)
- `security address-book`
- `security zones address-book`

## Corresponding Regression Test

The `snapshots/junos_commit_check/` snapshot contains one minimal config
per test case. The `test_parse_warnings` test in `lab_tests/test_labs.py`
asserts Batfish produces (or does not produce) fatal red flag warnings for
each, driven by `validation/parse_warnings.yaml`.
