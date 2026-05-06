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

Single vJunos-router node. For each grammar rule that accepts a prefix,
we attempt to commit a prefix with host bits set via `commit check`. The
device either rejects it or accepts it. IPv4 uses `192.168.1.111/24`;
IPv6 uses `2001:db8::1/32`.

The `checks.yaml` uses two check types:

- `commit_check_rejects`: asserts `commit check` fails
- `commit_check_accepts`: asserts `commit check` succeeds

Each check loads config lines, runs `commit check`, and rolls back.

## Running

```bash
# On EC2 with containerlab + vJunos image:
sudo containerlab deploy -t topology.clab.yml
# Wait for health (~5 min)
python -m lab_builder validate topology.clab.yml --checks checks.yaml
```

## Results (vJunos 25.4R1.12)

### IPv4: rejects host bits

- `routing-options static route`
- `routing-options aggregate route`
- `routing-options generate route`
- `protocols ospf area X area-range`
- `firewall filter X term T from destination-address`
- `firewall filter X term T then next-ip`
- `policy-options condition X if-route-exists`

### IPv4: accepts host bits

- `policy-options prefix-list`
- `policy-options policy-statement X from route-filter`
- `snmp client-list`
- `protocols bgp group X allow`
- `protocols mpls label-switched-path X install`
- `interfaces X unit Y family inet address`
- `interfaces X unit Y family inet address A vrrp-group N track route`

### IPv6: rejects host bits

- `routing-options rib inet6.0 static route`
- `routing-options rib inet6.0 aggregate route`
- `routing-options rib inet6.0 generate route`
- `protocols ospf3 area X area-range`
- `policy-options condition X if-route-exists` (table inet6.0)

### IPv6: accepts host bits

- `firewall family inet6 filter X term T from destination-address`
- `firewall family inet6 filter X term T then next-ip6`
- `policy-options prefix-list`
- `policy-options policy-statement X from route-filter`
- `interfaces X unit Y family inet6 address`
- `protocols bgp group X allow`

### Notable IPv4/IPv6 asymmetry

Junos rejects host bits in IPv4 `firewall filter` (destination-address
and next-ip) but accepts them in `firewall family inet6 filter`
(destination-address and next-ip6).

### Not tested (requires vSRX)

- `security nat` (pool address, match address, static-nat prefix)
- `security address-book`
- `security zones address-book`

## Corresponding Regression Test

The `snapshots/junos_commit_check/` snapshot contains one minimal config
per test case. The `test_parse_warnings` test in `lab_tests/test_labs.py`
asserts Batfish produces (or does not produce) fatal red flag warnings for
each, driven by `validation/parse_warnings.yaml`.
