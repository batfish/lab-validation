# junos_route_communities

Tests which community forms Junos accepts in the route-level `community`
statement under `routing-options static`, `aggregate`, and `generate`,
and what an eBGP peer receives for each.

Juniper's [`community (Routing Options)`][doc] reference says extended
communities are not supported at the `[edit routing-options]` hierarchy
and describes large communities as applying to static routes only.

[doc]: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/community-edit-routing-options.html

## Topology

```
sender master      (AS 65001) --- receiver (AS 65002)
       ge-0/0/0 10.0.12.0    <->  ge-0/0/0 10.0.12.1
sender DEFAULTS vr (AS 65001) --- receiver
       ge-0/0/1 10.0.13.0    <->  ge-0/0/1 10.0.13.1
```

`sender` exports every static, aggregate, and generated route to
`receiver` with `next-hop self` and no community action, so every
community on the receiver comes from a `community` statement under
`routing-options`. The master instance tests route-level `community`;
the `DEFAULTS` virtual-router tests `defaults community` without
affecting the master routes.

## Test routes

| Prefix         | Route type | `community`                     | Contributor                  |
| -------------- | ---------- | ------------------------------- | ---------------------------- |
| `10.10.0.0/24` | static     | `65001:10`                      |                              |
| `10.10.1.0/24` | static     | `large:65001:10:1`              |                              |
| `10.10.2.0/24` | static     | `[ 65001:10 large:65001:10:2 ]` |                              |
| `10.20.0.0/16` | aggregate  | `65001:20`                      | `10.20.1.0/24` discard       |
| `10.21.0.0/16` | aggregate  | `large:65001:21:1`              | `10.21.1.0/24` discard       |
| `10.30.0.0/16` | generate   | `65001:30`                      | `10.30.1.0/24` via 10.0.12.1 |
| `10.31.0.0/16` | generate   | `large:65001:31:1`              | `10.31.1.0/24` via 10.0.12.1 |

`DEFAULTS` virtual-router, with `static defaults community
large:65001:40:1`, `aggregate defaults community large:65001:50:1`, and
`generate defaults community large:65001:60:1`:

| Prefix         | Route type | Per-route `community` | Contributor                  |
| -------------- | ---------- | --------------------- | ---------------------------- |
| `10.40.0.0/24` | static     |                       |                              |
| `10.40.1.0/24` | static     | `65001:41`            |                              |
| `10.50.0.0/16` | aggregate  |                       | `10.50.1.0/24` discard       |
| `10.60.0.0/16` | generate   |                       | `10.60.1.0/24` via 10.0.13.1 |

## Results (vJunos-router 25.4R1.12)

### Commit checks

`checks.yaml` loads each form below on `sender` in six contexts:
`static route`, `static defaults`, `aggregate route`,
`aggregate defaults`, `generate route`, and `generate defaults`. All six
contexts behave the same:

| Community         | Result                                                         |
| ----------------- | -------------------------------------------------------------- |
| `65001:1`         | accepted                                                       |
| `no-export`       | accepted                                                       |
| `large:65001:1:1` | accepted                                                       |
| `target:65001:1`  | CLI rejects the `set`: `syntax error, expecting '[' or <data>` |
| `origin:65001:1`  | CLI rejects the `set`: `syntax error, expecting '[' or <data>` |

Extended communities are rejected when the `set` line is parsed, not at
`commit check`. Large communities are accepted on aggregate and
generated routes as well as static routes.

### Received routes

Every master-instance route reaches `receiver` with exactly the
configured communities, including the large communities on the
aggregate (`10.21.0.0/16`) and generated (`10.31.0.0/16`) routes.
Contributors carry no community.

`DEFAULTS` routes as received:

| Prefix         | Received communities |
| -------------- | -------------------- |
| `10.40.0.0/24` | `large:65001:40:1`   |
| `10.40.1.0/24` | `65001:41`           |
| `10.50.0.0/16` | `large:65001:50:1`   |
| `10.50.1.0/24` | `large:65001:40:1`   |
| `10.60.0.0/16` | `large:65001:60:1`   |
| `10.60.1.0/24` | `large:65001:40:1`   |

A per-route `community` replaces the `defaults` community rather than
adding to it (`10.40.1.0/24`). The aggregate and generated routes carry
only their own `defaults` community, not their contributors'
`large:65001:40:1`.

### Other observations

- `from protocol [ static aggregate generate ]` is stored as
  `from protocol static` and `from protocol aggregate`: Junos keeps no
  separate `generate` protocol match, and the generated routes still
  match the term.
- Without `next-hop self`, the generated routes and their contributors
  are advertised with the third-party next hop 10.0.12.1, which the
  receiver hides (`Hidden reason: Protocol nexthop is local`).
- For aggregate routes, the `as-path` field of `show route protocol bgp
detail | display json` carries a second line with the AGGREGATOR
  attribute (`AS path: 65001 I\nAggregator: 65001 1.1.1.1`).

## Batfish modeling notes

Batfish's grammar follows the documentation: `rosr_community` accepts
standard and large communities, while `roa_community` and
`rog_community` accept standard communities only. The
`aggregate ... community large:...` and `generate ... community large:...`
lines are reported as unrecognized syntax, and because the whole line is
discarded, Batfish never creates `10.21.0.0/16` or `10.31.0.0/16`. The
`aggregate defaults` and `generate defaults` large-community lines are
likewise unrecognized, so Batfish's `10.50.0.0/16` and `10.60.0.0/16`
carry no community. `test_main_rib_routes` (both nodes) and
`test_bgp_rib_routes` (`receiver`) are sickbayed against
batfish/batfish#10367.
