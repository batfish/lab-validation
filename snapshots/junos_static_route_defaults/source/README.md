# junos_static_route_defaults

Disambiguates how Junos `routing-options static defaults` inheritance is
scoped. Juniper's docs say `defaults` sets attributes "inherited by all
newly created static routes" and that per-route options "override any
options you configured in the defaults part," but they do not state
whether a `defaults` block is global, per routing table, or per
routing-instance. This lab answers that empirically by reading the
observed `preference` / `metric` / `tag` of static routes placed in five
different `static{}` blocks on one device.

## Topology

Single vJunos-router node `r1`. No links — every static route uses
`discard`, so each installs unconditionally and reports the attributes it
inherited (or overrode) without needing a reachable next-hop or a peer.

## The five static blocks (`source/configs/r1.cfg`)

| #   | Scope                            | Block defaults                | Route               | Per-route override |
| --- | -------------------------------- | ----------------------------- | ------------------- | ------------------ |
| 1   | master `inet.0`                  | pref 50, metric 100, tag 1000 | `10.200.1.0/24`     | — (inherits all)   |
| 1   | master `inet.0`                  | (same block)                  | `10.200.2.0/24`     | `preference 7`     |
| 2   | master `inet6.0` (`rib inet6.0`) | pref 60, tag 2000             | `2001:db8:200::/48` | —                  |
| 3   | `RED` virtual-router             | _none_                        | `10.210.1.0/24`     | —                  |
| 4   | `BLUE` virtual-router            | pref 80, tag 3000             | `10.220.1.0/24`     | —                  |

## Expected behavior

| Route               | Table         |          Expected pref | Expected metric | Expected tag |
| ------------------- | ------------- | ---------------------: | --------------: | -----------: |
| `10.200.1.0/24`     | `inet.0`      |                     50 |             100 |         1000 |
| `10.200.2.0/24`     | `inet.0`      |                  **7** |             100 |         1000 |
| `2001:db8:200::/48` | `inet6.0`     |                     60 |               — |         2000 |
| `10.210.1.0/24`     | `RED.inet.0`  | **5** (system default) |               — |            — |
| `10.220.1.0/24`     | `BLUE.inet.0` |                     80 |               — |         3000 |

If these hold, they jointly establish:

- **Per routing table.** `inet.0` (pref 50) and `inet6.0` (pref 60) carry
  independent defaults; neither bleeds into the other.
- **Per routing-instance.** `RED` has no defaults block, so its route
  takes the system default preference 5 — the master instance's defaults
  do **not** cascade into a routing-instance. `BLUE` has its own defaults
  (pref 80), independent of both master and `RED`.
- **No global cascade across hierarchy levels.** A `defaults` block only
  affects static routes in its own enclosing `static{}` statement.
- **Per-route override is field-by-field.** `10.200.2.0/24` overrides only
  `preference` (7); it still inherits `metric` 100 and `tag` 1000 from the
  block defaults.

## Observed results

Read from the running vJunos-router 25.4R1.12 node (`show route protocol
static detail`):

| Route               | Table         |  pref | metric |  tag |
| ------------------- | ------------- | ----: | -----: | ---: |
| `10.200.1.0/24`     | `inet.0`      |    50 |    100 | 1000 |
| `10.200.2.0/24`     | `inet.0`      | **7** |    100 | 1000 |
| `2001:db8:200::/48` | `inet6.0`     |    60 |      — | 2000 |
| `10.210.1.0/24`     | `RED.inet.0`  | **5** |      — |    — |
| `10.220.1.0/24`     | `BLUE.inet.0` |    80 |      — | 3000 |

Every value matches the expectation above, so all four conclusions hold:
defaults are scoped **per routing table** (inet.0 50 vs inet6.0 60),
**per routing-instance** (master 50 vs RED's system-default 5 vs BLUE's
own 80), with **no global cascade** across hierarchy levels, and per-route
overrides apply **field-by-field** (10.200.2.0/24 keeps the block's metric
100 and tag 1000 while overriding only preference to 7).

Note: in the brief `show route | display json` output the tag attribute is
emitted under the key `rt-tag` (not `tag`).

## Batfish modeling note

Batfish does not model the static `defaults` block: there is no
`ros_defaults` grammar rule, and `JuniperConfiguration` converts static
routes without inheriting defaults (unlike aggregate/generated routes,
which do inherit). Batfish therefore reports the bare static defaults
(preference 5, metric 0, no tag) for every static route here, so the
defaults-inherited routes mismatch the device. The `RED` route (system
default preference 5) is the one static route expected to match Batfish.
IPv6 (`inet6.0`) is captured for the source-of-truth record but is not
part of the validated comparison.

`test_main_rib_routes` is sickbayed against
https://github.com/batfish/batfish/issues/10017 until the `defaults`
block is modeled.
